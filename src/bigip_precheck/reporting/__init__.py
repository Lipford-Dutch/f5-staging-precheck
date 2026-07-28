"""Reporters: Rich console dashboard and schema-versioned JSON."""

from __future__ import annotations

from .console import render
from .json_report import SCHEMA_VERSION, build_report, write_report

__all__ = ["render", "SCHEMA_VERSION", "build_report", "write_report"]
