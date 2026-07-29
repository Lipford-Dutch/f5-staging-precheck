"""Pluggable checkers and the default registry builder.

Phase A ships System and HA checks. LTM/GTM (PR B) and the SNMP cross-check
layer (PR C) register the same way, so this is the single place that grows.
"""

from __future__ import annotations

from ..core.registry import Registry
from . import ha, system
from .base import Checker

__all__ = ["Checker", "build_default_registry", "system", "ha"]


def build_default_registry() -> Registry:
    """Return a registry populated with every built-in checker."""
    registry = Registry()
    for checker in (*system.checkers(), *ha.checkers()):
        registry.register(checker)
    return registry
