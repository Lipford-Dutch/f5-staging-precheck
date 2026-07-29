"""bigip-precheck — read-only F5 BIG-IP pre-upgrade / change-window validator.

The package is intentionally organised so that each layer can be tested in
isolation without a live device:

* :mod:`bigip_precheck.config`    — typed configuration (inventory, profiles, thresholds).
* :mod:`bigip_precheck.core`      — result model, registry, orchestration, GO/NO-GO gate.
* :mod:`bigip_precheck.clients`   — iControl REST (SNMP / TMSH land in later phases).
* :mod:`bigip_precheck.checkers`  — the pluggable checks themselves.
* :mod:`bigip_precheck.reporting` — console + JSON reporters.
* :mod:`bigip_precheck.logging`   — audit trail, redaction, report integrity.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
