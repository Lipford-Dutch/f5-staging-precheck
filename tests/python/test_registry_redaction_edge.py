"""Registry error paths, core lazy-import surface, and adversarial redaction.

Redaction is security-sensitive, so these go beyond line coverage: they probe
shapes an attacker or a noisy device could produce (secrets nested in lists,
mixed-case header keys, secrets embedded in free text, non-string dict keys)."""

from __future__ import annotations

import pytest

from bigip_precheck.checkers.base import Checker
from bigip_precheck.core.exceptions import ConfigError
from bigip_precheck.core.registry import Registry
from bigip_precheck.redaction import REDACTED, redact, redact_text


class _Noop(Checker):
    def __init__(self, name: str, deps: tuple[str, ...] = ()) -> None:
        self.name = name
        self.depends_on = deps

    def run(self, ctx):  # pragma: no cover - never executed
        return []


# -- registry error paths --------------------------------------------------
def test_register_rejects_empty_name():
    with pytest.raises(ConfigError, match="no name"):
        Registry().register(_Noop(""))


def test_register_rejects_duplicate():
    reg = Registry()
    reg.register(_Noop("a"))
    with pytest.raises(ConfigError, match="duplicate"):
        reg.register(_Noop("a"))


def test_get_unknown_raises():
    with pytest.raises(ConfigError, match="unknown check"):
        Registry().get("ghost")


def test_select_unknown_dependency_raises():
    reg = Registry()
    reg.register(_Noop("a", deps=("missing",)))
    with pytest.raises(ConfigError, match="unknown check"):
        reg.select(["a"])


def test_names_are_sorted_and_all_returns_instances():
    reg = Registry()
    reg.register(_Noop("z"))
    reg.register(_Noop("a"))
    assert reg.names() == ["a", "z"]
    assert {c.name for c in reg.all()} == {"a", "z"}


def test_select_none_orders_all_deps_first():
    reg = Registry()
    reg.register(_Noop("leaf"))
    reg.register(_Noop("root", deps=("leaf",)))
    ordered = [c.name for c in reg.select(None)]
    assert ordered.index("leaf") < ordered.index("root")


# -- core lazy import surface ---------------------------------------------
def test_core_lazy_exports_resolve():
    from bigip_precheck import core

    assert core.Registry is Registry
    from bigip_precheck.core.orchestrator import Orchestrator as O

    assert core.Orchestrator is O


def test_core_unknown_attr_raises():
    from bigip_precheck import core

    with pytest.raises(AttributeError):
        _ = core.DoesNotExist


# -- adversarial redaction -------------------------------------------------
def test_redact_secret_in_nested_list():
    data = {"peers": [{"password": "p"}, {"token": "t"}, {"ok": "keep"}]}
    out = redact(data)
    assert out["peers"][0]["password"] == REDACTED
    assert out["peers"][1]["token"] == REDACTED
    assert out["peers"][2]["ok"] == "keep"


def test_redact_key_match_is_case_insensitive():
    out = redact({"Set-Cookie": "abc", "AUTHORIZATION": "Bearer z"})
    assert out["Set-Cookie"] == REDACTED
    assert out["AUTHORIZATION"] == REDACTED


def test_redact_text_scrubs_inline_secrets():
    assert "SEKRET" not in redact_text("X-F5-Auth-Token: SEKRET")
    assert "dGVzdDp0ZXN0" not in redact_text("Authorization: Basic dGVzdDp0ZXN0")
    assert "hunter2" not in redact_text('{"password": "hunter2"}')


def test_redact_preserves_non_string_keys_and_scalars():
    out = redact({1: "one", 2.0: "two", "n": 5, "b": True})
    assert out == {1: "one", 2.0: "two", "n": 5, "b": True}


def test_redact_tuple_becomes_list_and_is_scrubbed():
    out = redact(({"token": "t"}, "plain"))
    assert isinstance(out, list)
    assert out[0]["token"] == REDACTED
    assert out[1] == "plain"


def test_redact_bytes_passthrough_unchanged():
    # bytes are not str; redact leaves them as-is (documented behaviour).
    payload = b"password=secret"
    assert redact(payload) is payload
