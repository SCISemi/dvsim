# Copyright lowRISC contributors (OpenTitan project).
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

"""Machine-readable queries of DVSim configuration data."""

import json
import re
from copy import deepcopy
from pathlib import Path

from dvsim.flow.base import FlowCfg
from dvsim.flow.one_shot import OneShotCfg
from dvsim.job.deploy import CompileOneShot, CompileSim
from dvsim.sim.flow import SimCfg
from dvsim.utils import find_and_substitute_wildcards


def _json_default(value: object) -> str:
    if isinstance(value, Path):
        return str(value)
    msg = f"Configuration contains an unsupported value of type {type(value).__name__}."
    raise ValueError(msg)


def _unresolved(value: object, wildcards: list[str]) -> bool:
    if isinstance(value, str):
        return any(name in wildcards for name in re.findall(r"{([A-Za-z0-9_]+)}", value))
    if isinstance(value, dict):
        return any(_unresolved(item, wildcards) for item in value.values())
    if isinstance(value, list):
        return any(_unresolved(item, wildcards) for item in value)
    return False


def _records(cfg: FlowCfg, name: str) -> list[dict]:
    values = cfg._config_values  # noqa: SLF001
    if (
        name
        and name not in values
        and not (name == "build_mode" and isinstance(cfg, SimCfg | OneShotCfg) and cfg.items)
    ):
        msg = f"Unknown configuration variable {name!r} in {cfg.name!r}."
        raise ValueError(msg)

    # Ordinary path queries do not need build objects. Simulation build modes
    # are selected through tests/regressions, exactly as in a normal invocation.
    config_only = name in {
        "name",
        "tool",
        "proj_root",
        "scratch_root",
        "scratch_base_path",
        "scratch_path",
        "branch",
        "timestamp",
        "timestamp_long",
    } and not _unresolved(values[name], ["build_mode"])
    if not isinstance(cfg, SimCfg | OneShotCfg) or not cfg.items or config_only:
        return [{"configuration": cfg.name, "config": values}]

    if isinstance(cfg, SimCfg):
        cfg._create_build_and_run_list()  # noqa: SLF001
        if not cfg.build_list:
            raise ValueError("No builds matched --items; select a test or regression.")
        builds = [CompileSim(mode, cfg) for mode in cfg.build_list]
    else:
        # One-shot flows build every configured mode rather than selecting tests.
        builds = [CompileOneShot(mode, cfg) for mode in cfg.build_modes]
        if not builds:
            raise ValueError("No build modes are configured.")

    records = []
    for build in builds:
        resolved = deepcopy(values)
        # Use the actual build's final attributes, including tool adjustments.
        for key in build.mandatory_cmd_attrs | build.mandatory_misc_attrs:
            if key in resolved and key != "name":
                resolved[key] = getattr(build, key)
        resolved["build_mode"] = build.build_mode
        resolved = find_and_substitute_wildcards(
            resolved,
            cfg.__dict__ | build.__dict__,
            [key for key in cfg.ignored_wildcards if key != "build_mode"],
        )
        records.append(
            {
                "configuration": cfg.name,
                "build_mode": build.build_mode,
                "config": resolved,
            }
        )
    return records


def print_config(cfg: FlowCfg, name: str) -> None:
    """Print one unambiguous value, or JSON configuration records."""
    cfg.prune_selected_cfgs()
    if not cfg.cfgs:
        raise ValueError("No configurations matched --select-cfgs.")
    if name and len(cfg.cfgs) != 1:
        raise ValueError("Select one configuration with --select-cfgs for a named query.")

    records = [record for child in cfg.cfgs for record in _records(child, name)]
    if not name:
        data = records[0]["config"] if len(records) == 1 else records
        print(json.dumps(data, default=_json_default, indent=2, sort_keys=True))
        return

    if len(records) != 1:
        if isinstance(cfg.cfgs[0], OneShotCfg):
            raise ValueError(
                "A named query requires exactly one configured build mode. "
                "Use --print-config without a name to inspect all build modes."
            )
        raise ValueError("Select --items matching exactly one build mode for a named query.")
    value = records[0]["config"][name]
    if _unresolved(value, cfg.cfgs[0].ignored_wildcards):
        msg = (
            f"Configuration variable {name!r} needs additional build or run context. "
            "Use --items to select a test for build-dependent values; "
            "run-dependent values cannot be queried as resolved values."
        )
        raise ValueError(msg)
    if isinstance(value, str | Path):
        print(value)
    else:
        print(json.dumps(value, default=_json_default, indent=2, sort_keys=True))
