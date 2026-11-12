"""Load a flow file and work out how its steps connect."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

STEP_TYPES = {"message", "question", "handover", "end"}
FINAL_TYPES = {"handover", "end"}


@dataclass
class Flow:
    name: str
    start: str
    steps: dict[str, dict]

    def step_type(self, step_id: str) -> str:
        return str(self.steps[step_id].get("type", ""))

    def targets(self, step_id: str) -> list[tuple[str, str]]:
        """Every step this step can lead to, as (label, target) pairs."""
        step = self.steps[step_id]
        found: list[tuple[str, str]] = []
        if step.get("next"):
            found.append(("next", str(step["next"])))
        for option in step.get("options") or []:
            if option.get("next"):
                label = str((option.get("match") or ["option"])[0])
                found.append((label, str(option["next"])))
        no_match = step.get("no_match") or {}
        if no_match.get("then"):
            found.append(("no match", str(no_match["then"])))
        return found

    def reachable_from(self, step_id: str) -> set[str]:
        seen: set[str] = set()
        stack = [step_id]
        while stack:
            current = stack.pop()
            if current in seen or current not in self.steps:
                continue
            seen.add(current)
            stack.extend(target for _, target in self.targets(current))
        return seen


def _keyword(value) -> str:
    """YAML reads a bare yes or no as true or false. Turn them back into words."""
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return str(value)


def _clean_step(step: dict | None) -> dict:
    step = dict(step or {})
    options = []
    for option in step.get("options") or []:
        option = dict(option)
        match = option.get("match")
        if match is None:
            match = []
        elif not isinstance(match, list):
            match = [match]
        option["match"] = [_keyword(m) for m in match]
        options.append(option)
    if options:
        step["options"] = options
    return step


def parse_flow(data: dict) -> Flow:
    if not isinstance(data, dict):
        raise ValueError("A flow file must contain a YAML mapping at the top level")
    steps = data.get("steps") or {}
    if not isinstance(steps, dict):
        raise ValueError("'steps' must be a mapping of step names to steps")
    return Flow(
        name=str(data.get("flow", "unnamed")),
        start=str(data.get("start", "")),
        steps={str(k): _clean_step(v) for k, v in steps.items()},
    )


def load_flow(path: str | Path) -> Flow:
    with open(path, encoding="utf-8") as handle:
        return parse_flow(yaml.safe_load(handle))
