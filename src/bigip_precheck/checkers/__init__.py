"""Pluggable checkers and the default registry builder.

Phases A/B ship System, HA, LTM and GTM checks. The SNMP cross-check layer
(PR C) registers the same way, so this is the single place that grows.
"""

from __future__ import annotations

from ..core.registry import Registry
from . import gtm, ha, ltm, system
from .base import Checker

__all__ = ["Checker", "build_default_registry", "system", "ha", "ltm", "gtm"]


def build_default_registry() -> Registry:
    """Return a registry populated with every built-in checker."""
    registry = Registry()
    for checker in (*system.checkers(), *ha.checkers(), *ltm.checkers(), *gtm.checkers()):
        registry.register(checker)
    return registry
