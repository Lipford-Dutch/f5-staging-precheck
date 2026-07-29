"""Device clients. Only iControl REST ships in phase A; SNMP/TMSH follow."""

from __future__ import annotations

from .rest import IControlRestClient, RestClient

__all__ = ["IControlRestClient", "RestClient"]
