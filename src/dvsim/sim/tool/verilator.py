# Copyright lowRISC contributors (OpenTitan project).
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

"""EDA tool plugin providing Verilator support to DVSim."""

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from dvsim.job.data import JobSpec
from dvsim.sim.data import CodeCoverageMetrics, CoverageMetrics

if TYPE_CHECKING:
    from dvsim.job.deploy import Deploy

__all__ = ("Verilator",)


class Verilator:
    """Implement Verilator tool support."""

    @staticmethod
    def get_cov_summary_table(cov_report_path: Path) -> tuple[Sequence[Sequence[str]], str]:
        """Get a coverage summary.

        Args:
            cov_report_path: path to the raw coverage report

        Returns:
            tuple of, List of metrics and values, and final coverage total

        """

        raise RuntimeError("Coverage not supported for Verilator")

    @staticmethod
    def get_job_runtime(_job: JobSpec, log_text: Sequence[str]) -> tuple[float, str]:
        """Return the job runtime (wall clock time) along with its units.

        EDA tools indicate how long the job ran in terms of CPU time in the log
        file. This method invokes the tool specific method which parses the log
        text and returns the runtime as a floating point value followed by its
        units as a tuple.

        Args:
            job: The job that was run.
            log_text: is the job's log file contents as a list of lines.

        Returns:
            a tuple of (runtime, units).

        Raises:
            RuntimeError: exception if the search pattern is not found.

        """

        raise NotImplementedError("Verilator is unsupported for job runtime extraction.")

    @staticmethod
    def get_simulated_time(_job: JobSpec, log_text: Sequence[str]) -> tuple[float, str]:
        """Return the simulated time along with its units.

        EDA tools indicate how long the design was simulated for in the log file.
        This method invokes the tool specific method which parses the log text and
        returns the simulated time as a floating point value followed by its
        units (typically, pico|nano|micro|milliseconds) as a tuple.

        Args:
            job: The job that was run
            log_text: is the job's log file contents as a list of lines.

        Returns:
            a tuple of (simulated time, units).

        Raises:
            RuntimeError: exception if the search pattern is not found.

        """

        raise NotImplementedError("Verilator is unsupported for simulation time extraction.")


    @staticmethod
    def get_coverage_metrics(raw_metrics: Mapping[str, float | None] | None) -> CoverageMetrics:
        """Get a CoverageMetrics model from raw coverage data.

        Args:
            raw_metrics: raw coverage metrics as parsed from the tool.

        Returns:
            CoverageMetrics model.

        """
        if raw_metrics is None:
            return CoverageMetrics(code=None, assertion=None, functional=None)

        return CoverageMetrics(
            functional=raw_metrics.get("covergroup"),
            assertion=raw_metrics.get("assertion"),
            code=CodeCoverageMetrics(
                block=raw_metrics.get("block"),
                line_statement=raw_metrics.get("statement"),
                branch=raw_metrics.get("branch"),
                condition_expression=raw_metrics.get("cond"),
                toggle=raw_metrics.get("toggle"),
                fsm=raw_metrics.get("fsm"),
            ),
        )

    @staticmethod
    def set_additional_attrs(deploy: "Deploy") -> None:
        """Define any additional tool-specific attrs on the deploy object.

        Args:
            deploy: the deploy object to mutate.

        """
