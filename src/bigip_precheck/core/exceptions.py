"""Typed exception hierarchy.

Distinguishing these lets the orchestrator decide whether a failure is the
*operator's* fault (config), the *device's* fault (connectivity / auth), or a
*bug* — and lets checks fail loud rather than silently passing.
"""

from __future__ import annotations


class PrecheckError(Exception):
    """Base class for every error raised by bigip-precheck."""


class ConfigError(PrecheckError):
    """Invalid or missing configuration supplied by the operator."""


class ClientError(PrecheckError):
    """A device client (REST/SNMP/TMSH) could not complete a request."""


class AuthError(ClientError):
    """Authentication or authorisation against the device failed."""


class ConnectionFailed(ClientError):
    """The device was unreachable or the request timed out."""


class UnexpectedResponse(ClientError):
    """The device responded, but not in a shape the client could parse."""


__all__ = [
    "PrecheckError",
    "ConfigError",
    "ClientError",
    "AuthError",
    "ConnectionFailed",
    "UnexpectedResponse",
]
