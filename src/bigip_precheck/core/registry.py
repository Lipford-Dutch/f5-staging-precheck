"""Checker registry: registration, lookup, profile filtering, dependency order."""

from __future__ import annotations

from collections import deque

from ..checkers.base import Checker
from .exceptions import ConfigError


class Registry:
    """Holds the known checkers and resolves an ordered run list."""

    def __init__(self) -> None:
        self._checkers: dict[str, Checker] = {}

    def register(self, checker: Checker) -> Checker:
        """Register a checker instance. Raises on empty or duplicate name."""
        if not checker.name:
            raise ConfigError(f"{type(checker).__name__} has no name")
        if checker.name in self._checkers:
            raise ConfigError(f"duplicate checker name: {checker.name}")
        self._checkers[checker.name] = checker
        return checker

    def all(self) -> list[Checker]:
        return list(self._checkers.values())

    def names(self) -> list[str]:
        return sorted(self._checkers)

    def get(self, name: str) -> Checker:
        try:
            return self._checkers[name]
        except KeyError as exc:
            raise ConfigError(f"unknown check: {name}") from exc

    def select(self, names: list[str] | None) -> list[Checker]:
        """Return checkers for ``names`` (or all), topologically ordered by deps.

        Unknown names raise. Dependencies are always included even if a profile
        omitted them, so a check never runs with an unmet prerequisite.
        """
        if names:
            unknown = [n for n in names if n not in self._checkers]
            if unknown:
                raise ConfigError(f"unknown check(s): {', '.join(sorted(unknown))}")
            wanted = set(names)
        else:
            wanted = set(self._checkers)

        # Pull in transitive dependencies.
        queue = deque(wanted)
        while queue:
            n = queue.popleft()
            for dep in self._checkers[n].depends_on:
                if dep not in self._checkers:
                    raise ConfigError(f"check '{n}' depends on unknown check '{dep}'")
                if dep not in wanted:
                    wanted.add(dep)
                    queue.append(dep)

        return self._topo_order(wanted)

    def _topo_order(self, wanted: set[str]) -> list[Checker]:
        ordered: list[Checker] = []
        visited: dict[str, int] = {}  # 0=visiting, 1=done

        def visit(name: str, stack: tuple[str, ...]) -> None:
            state = visited.get(name)
            if state == 1:
                return
            if state == 0:
                cycle = " -> ".join((*stack, name))
                raise ConfigError(f"dependency cycle: {cycle}")
            visited[name] = 0
            for dep in self._checkers[name].depends_on:
                if dep in wanted:
                    visit(dep, (*stack, name))
            visited[name] = 1
            ordered.append(self._checkers[name])

        for name in sorted(wanted):
            visit(name, ())
        return ordered


__all__ = ["Registry"]
