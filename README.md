<!--
# Copyright lowRISC contributors (OpenTitan project).
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0
-->
# DVSim

![OpenTitan logo](./doc/opentitan-logo.png)

## About the project

[OpenTitan](https://opentitan.org) is an open source silicon Root of Trust (RoT) project.
OpenTitan will make the silicon RoT design and implementation more transparent, trustworthy, and secure for enterprises, platform providers, and chip manufacturers.
OpenTitan is administered by [lowRISC CIC](https://www.lowrisc.org) as a collaborative project to produce high quality, open IP for instantiation as a full-featured product.
See the [OpenTitan site](https://opentitan.org) and [OpenTitan docs](https://opentitan.org/book/) for more information about the project.

## About this repository

This repository contains **DVSim** which is a build and run system written in Python that runs a variety of EDA tool flows.
There are multiple steps involved in running EDA tool flows.
DVSim encapsulates them all to provide a single, standardized command-line interface to launch them.
While DVSim was written to support OpenTitan, it can be used for any ASIC project.

All EDA tool flows on OpenTitan are launched using the DVSim tool.
The following flows are currently supported:

* Simulations
* Coverage Unreachability Analysis (UNR)
* Formal (formal property verification (FPV), and connectivity)
* Lint (semantic and stylistic)
* Synthesis
* CDC
* RDC

### Installation

#### Using nix and direnv

If you have [Nix](https://nixos.org/download/) and [direnv](https://direnv.net/) installed, then it's as simple as `direnv allow .`.

New to Nix? Perhaps checkout this [installer](https://determinate.systems/posts/determinate-nix-installer/) which will enable flakes by default.

#### Using uv direct

The recommended way of installing DVSim is inside a virtual environment to isolate the dependencies from your system python install.
We use the `uv` tool for python dependency management and creating virtual environments.

First make sure you have `uv` installed, see the [installation documentation](https://docs.astral.sh/uv/getting-started/installation/) for details and alternative installation methods.
There is a python package that can be installed with `pip install uv`, however the standalone installer is preferred.

##### macOS and Linux

```console
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
uv sync
```

From there you can run the `dvsim` tool.

##### Windows (Powershell)

```console
irm https://astral.sh/uv/install.ps1 | iex
uv venv
uv sync
```

From there you can run the `dvsim` tool.

### Using DVSim

For further information on how to use DVsim with OpenTitan see [Getting Started](https://opentitan.org/book/doc/getting_started/index.html)

#### Querying configuration from external builds

Use `--print-config NAME` to obtain a configuration value without launching build
or simulation jobs. Strings and paths are printed directly; other values are
pretty-printed as JSON with two-space indentation. Query mode suppresses routine
informational logs by default; warnings and errors go to stderr and unsuccessful
queries exit nonzero. Use
`--verbose` or `--log-level` to request additional diagnostics.
Put the configuration filename before the option, since its argument is optional.

```sh
dvsim path/to/config.hjson --print-config scratch_path
dvsim path/to/config.hjson --tool xcelium -i smoke_test --print-config build_dir
dvsim path/to/config.hjson --print-config
```

Without a name, the output is a JSON object containing loaded HJSON fields and
configuration context such as `scratch_root`, `branch`, and command-line options.
Imports, overrides and wildcard expansion follow the normal configuration loader.
Runtime objects are excluded. Templates requiring build or run context remain in
the full JSON output; a named query fails if its value remains unresolved.

Query mode preserves the normal default item, `smoke`. For simulation builds,
pass `--items` to select different tests or regressions and resolve their build
modes, options and paths. Pass an empty `--items` option to inspect configuration
without selecting a build (for example, `dvsim config.hjson --items --print-config`).
Build context is resolved using the normal build preparation code, without
executing jobs. One-shot flows such as superlint, synthesis and formal resolve
all configured build modes using their normal build preparation code. Named
queries require one configuration and one build; use
`--select-cfgs` for primary configuration files. When multiple configurations or
builds are selected, full JSON output is an array of records with `configuration`,
optional `build_mode`, and `config` fields. Run-dependent values such as test seeds
cannot be queried as resolved values.

Configuration loading still initializes the scratch root and may evaluate
configuration commands. Query mode does not deploy jobs, purge output directories,
create a deployment dump or generate reports, and cannot be combined with `--remote`.
With `--build-unique`, paths include the timestamp of the query invocation; a later
invocation has its own timestamp.

A standalone Makefile can query a path once when its caller has not supplied it:

```make
DVSIM_CFG ?= path/to/config.hjson

ifndef SCRATCH_PATH
SCRATCH_PATH := $(shell dvsim "$(DVSIM_CFG)" --print-config scratch_path)
ifneq ($(.SHELLSTATUS),0)
$(error Failed to query dvsim scratch_path)
endif
ifeq ($(strip $(SCRATCH_PATH)),)
$(error dvsim scratch_path is empty)
endif
endif

export SCRATCH_PATH
```

When dvsim invokes this Makefile, supply the path through the configuration's
existing exports mechanism:

```hjson
exports: [
  { SCRATCH_PATH: "{scratch_path}" }
]
```

## History

DVSim development started in the main OpenTitan repository under `utils/dvsim`.
This repository contains the code that origionaly lived there, as well as the full git history copied over as generated by `git subtree split -p utils/dvsim`.

## Documentation

The project contains comprehensive documentation of all IPs and tools.
You can access it [online at opentitan.org/book/](https://opentitan.org/book/).

### Other related documents

* [Testplanner tool](./doc/testplanner.md)
* [Design document](./doc/design_doc.md)
* [Glossary](./doc/glossary.md)

## How to contribute

Have a look at [CONTRIBUTING](https://github.com/lowRISC/opentitan/blob/master/CONTRIBUTING.md) and our [documentation on project organization and processes](https://opentitan.org/book/doc/project_governance/README.md) for guidelines on how to contribute code to this repository.

## Licensing

Unless otherwise noted, everything in this repository is covered by the Apache License, Version 2.0 (see [LICENSE](https://github.com/lowRISC/opentitan/blob/master/LICENSE) for full text).

## Bugs

Please see [link](https://github.com/lowRISC/dvsim/issues) for a list of open bugs and feature requests.
