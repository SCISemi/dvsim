# Copyright lowRISC contributors (OpenTitan project).
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

"""Exercise configuration queries through the real CLI and HJSON resolver."""

import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from dvsim.cli import main
from dvsim.cli.run import parse_args
from dvsim.flow.base import FlowCfg


@pytest.fixture
def config_cli(tmp_path, monkeypatch):
    """Create a simulation config and forbid job execution and purging."""

    def unexpected(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Configuration queries must not execute or purge jobs")

    monkeypatch.setattr(FlowCfg, "deploy_objects", unexpected)
    monkeypatch.setattr(FlowCfg, "purge", unexpected)
    monkeypatch.setattr(FlowCfg, "create_deploy_objects", unexpected)
    monkeypatch.delenv("SCRATCH_ROOT", raising=False)
    config = {
        "name": "example",
        "flow": "sim",
        "tool": "xcelium",
        "rel_path": "dv",
        "scratch_base_path": "{scratch_root}/{branch}",
        "scratch_path": "{scratch_base_path}/{name}/{tool}",
        "build_dir": "{scratch_path}/build/{build_mode}",
        "run_dir": "{scratch_path}/run/{test}/{seed}",
        "build_modes": [
            {"name": "waves_off"},
            {"name": "xprop"},
            {"name": "alternate", "build_opts": ["ALT"]},
        ],
        "tests": [
            {"name": "smoke", "reseed": 1},
            {"name": "other", "build_mode": "alternate", "reseed": 1},
        ],
        "flow_makefile": "never-executed.mk",
        "sv_flist_gen_cmd": "true",
        "sv_flist_gen_dir": "{scratch_path}/flist",
        "sv_flist_gen_opts": [],
        "build_fail_patterns": [],
        "build_pass_patterns": [],
        "build_timeout_mins": 0,
        "cov_db_dir": "",
        "exports": [{"SCRATCH_PATH": "{scratch_path}"}],
    }
    cfg_path = tmp_path / "config.hjson"
    cfg_path.write_text(json.dumps(config))
    root = Path(__file__).resolve().parents[1]
    args = [
        str(cfg_path),
        "--proj-root",
        str(root),
        "--scratch-root",
        str(tmp_path / "scratch"),
        "--branch",
        "test",
    ]
    return args, config, cfg_path, tmp_path / "scratch"


def test_scratch_path(config_cli, capsys):
    """Named queries emit a plain value and skip execution, even with --purge."""
    args, _, _, scratch = config_cli
    main([*args, "--purge", "--print-config", "scratch_path"])
    assert capsys.readouterr().out == f"{scratch}/test/example/xcelium\n"
    assert not (scratch / "FUSESOC_IGNORE").exists()
    assert not list(scratch.glob("deploy_*.json"))


def test_json_config(config_cli, capsys):
    """Full queries retain structured HJSON data and exclude runtime objects."""
    args, _, _, scratch = config_cli
    main([*args, "--items", "--print-config"])
    data = json.loads(capsys.readouterr().out)
    assert data["scratch_path"] == f"{scratch}/test/example/xcelium"
    assert data["tests"][0]["name"] == "smoke"
    assert data["build_dir"].endswith("/{build_mode}")
    assert data["exports"] == [{"SCRATCH_PATH": data["scratch_path"]}]
    assert "args" not in data
    assert "workspace_cfg" not in data


@pytest.mark.parametrize(("test", "mode"), [("smoke", "default"), ("other", "alternate")])
def test_build_path(config_cli, capsys, test, mode):
    """Selected tests provide the same build-mode context as normal builds."""
    args, _, _, scratch = config_cli
    main([*args, "-i", test, "--print-config", "build_dir"])
    assert capsys.readouterr().out == f"{scratch}/test/example/xcelium/build/{mode}\n"


@pytest.mark.parametrize("query_args", [[], ["--print-config"], ["--print-config", "build_dir"]])
@pytest.mark.parametrize("item_args", [[], ["--items"], ["--items", "other"]])
def test_item_defaults(query_args, item_args):
    """Normal runs and queries preserve the smoke default and explicit selections."""
    args = parse_args(["config.hjson", "--max-parallel", "1", *item_args, *query_args])
    expected = ["smoke"] if not item_args else item_args[1:]
    assert args.items == expected


def test_default_build_path(config_cli, capsys):
    """Build-dependent queries resolve the smoke build when no item is supplied."""
    args, _, _, scratch = config_cli
    main([*args, "--print-config", "build_dir"])
    assert capsys.readouterr().out == f"{scratch}/test/example/xcelium/build/default\n"


@pytest.fixture
def one_shot_cli(config_cli):
    """Model a superlint file-list directory that depends on the build mode."""
    args, config, cfg_path, scratch = config_cli
    config.update(
        {
            "flow": "formal",
            "sub_flow": "superlint",
            "tool": "jaspergold",
            "run_dir": "",
            "build_modes": [],
            "sv_flist_gen_dir": "{build_dir}/example/syn-vcs",
            "build_cmd": "true",
            "build_log": "{build_dir}/build.log",
            "pre_build_cmds": [],
            "post_build_cmds": [],
            "post_build_opts": [],
            "report_cmd": "true",
            "report_opts": [],
        }
    )
    cfg_path.write_text(json.dumps(config))
    return args, config, cfg_path, scratch


def test_one_shot_file_list_directory(one_shot_cli, capsys):
    """Named and full superlint queries use the same resolved build context."""
    args, _, _, scratch = one_shot_cli
    expected = f"{scratch}/test/example/jaspergold/build/default/example/syn-vcs"
    main([*args, "--print-config", "sv_flist_gen_dir"])
    assert capsys.readouterr().out == expected + "\n"
    main([*args, "--print-config"])
    assert json.loads(capsys.readouterr().out)["sv_flist_gen_dir"] == expected
    main([*args, "--print-config", "build_mode"])
    assert capsys.readouterr().out == "default\n"
    main([*args, "--items", "--print-config"])
    assert "{build_mode}" in json.loads(capsys.readouterr().out)["sv_flist_gen_dir"]


def test_one_shot_multiple_builds(one_shot_cli, capsys):
    """Multiple configured one-shot builds are identified without guessing a mode."""
    args, config, cfg_path, _ = one_shot_cli
    config["build_modes"] = [{"name": "alternate"}]
    cfg_path.write_text(json.dumps(config))
    with pytest.raises(SystemExit) as error:
        main([*args, "--print-config", "sv_flist_gen_dir"])
    assert error.value.code == 1
    assert capsys.readouterr().out == ""
    main([*args, "--print-config"])
    records = json.loads(capsys.readouterr().out)
    assert [record["build_mode"] for record in records] == ["default", "alternate"]
    assert records[0]["config"]["sv_flist_gen_dir"] != records[1]["config"]["sv_flist_gen_dir"]


@pytest.mark.parametrize(
    "extra",
    [
        ["--print-config", "missing"],
        ["--items", "--print-config", "build_dir"],
        ["-i", "smoke", "--print-config", "run_dir"],
        ["-i", "smoke", "other", "--print-config", "build_dir"],
        ["-i", "missing", "--print-config", "build_dir"],
    ],
)
def test_invalid_query(config_cli, capsys, extra):
    """Invalid, unresolved and ambiguous queries fail without partial stdout."""
    args, _, _, _ = config_cli
    with pytest.raises(SystemExit) as error:
        main([*args, *extra])
    assert error.value.code == 1
    assert capsys.readouterr().out == ""


def test_multiple_builds_json(config_cli, capsys):
    """JSON identifies each build and preserves the final build options."""
    args, _, _, _ = config_cli
    main([*args, "-i", "smoke", "other", "--print-config"])
    data = json.loads(capsys.readouterr().out)
    assert [row["build_mode"] for row in data] == ["default", "alternate"]
    assert data[1]["config"]["build_opts"] == ["ALT"]


@pytest.mark.parametrize(
    ("name", "expected"),
    [("build_mode", "alternate\n"), ("build_opts", '[\n  "ALT"\n]\n')],
)
def test_named_build_values(config_cli, capsys, name, expected):
    """Named queries include derived build modes and selected build options."""
    args, _, _, _ = config_cli
    main([*args, "-i", "other", "--print-config", name])
    assert capsys.readouterr().out == expected


def test_imports_and_overrides(config_cli, capsys):
    """Queries obey imported configuration, HJSON overrides and CLI tool selection."""
    args, config, cfg_path, scratch = config_cli
    imported = cfg_path.with_name("paths.hjson")
    imported.write_text(json.dumps({"scratch_path": config.pop("scratch_path")}))
    config["import_cfgs"] = [str(imported)]
    config["overrides"] = [{"name": "name", "value": "renamed"}]
    cfg_path.write_text(json.dumps(config))
    main([*args, "--tool", "vcs", "--print-config", "scratch_path"])
    assert capsys.readouterr().out == f"{scratch}/test/renamed/vcs\n"


def test_configuration_selection(config_cli, capsys):
    """Primary config queries require selection for a named value."""
    args, config, cfg_path, _ = config_cli
    other = cfg_path.with_name("other.hjson")
    config["name"] = "second"
    other.write_text(json.dumps(config))
    primary = cfg_path.with_name("primary.hjson")
    primary.write_text(
        json.dumps(
            {
                "name": "primary",
                "flow": "sim",
                "rel_path": "dv",
                "use_cfgs": [str(cfg_path), str(other)],
            }
        )
    )
    args = [str(primary), *args[1:]]
    with pytest.raises(SystemExit) as error:
        main([*args, "--print-config", "scratch_path"])
    assert error.value.code == 1
    assert capsys.readouterr().out == ""
    main([*args, "--print-config"])
    assert len(json.loads(capsys.readouterr().out)) == 2
    main([*args, "--select-cfgs", "second", "--print-config", "name"])
    assert capsys.readouterr().out == "second\n"
    with pytest.raises(SystemExit) as error:
        main([*args, "--select-cfgs", "missing", "--print-config"])
    assert error.value.code == 1


@pytest.mark.parametrize("logging_args", [[], ["--verbose"], ["--log-level", "INFO"]])
def test_query_logging(config_cli, logging_args):
    """Queries are quiet by default and honor explicit logging requests."""
    args, _, _, scratch = config_cli
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from dvsim.cli import main; main()",
            *args,
            "--print-config",
            "scratch_path",
            *logging_args,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == f"{scratch}/test/example/xcelium\n"
    if logging_args:
        assert "[proj_root]" in result.stderr
        assert "[scratch_path]" in result.stderr
    else:
        assert result.stderr == ""


def test_makefile_query(config_cli, tmp_path):
    """GNU Make captures only the requested value and receives no routine logs."""
    args, _, _, scratch = config_cli
    command = shlex.join(
        [
            sys.executable,
            "-c",
            "from dvsim.cli import main; main()",
            *args,
            "--print-config",
            "scratch_path",
        ],
    )
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        f"SCRATCH_PATH := $(shell {command})\n"
        ".PHONY: show\nshow:\n\t@printf '%s\\n' '$(SCRATCH_PATH)'\n",
    )
    result = subprocess.run(
        ["make", "--no-print-directory", "-f", str(makefile), "show"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == f"{scratch}/test/example/xcelium\n"
    assert result.stderr == ""
