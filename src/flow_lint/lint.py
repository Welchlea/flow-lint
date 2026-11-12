"""The checks that find problems in a flow before a user does."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .model import FINAL_TYPES, STEP_TYPES, Flow

ERROR, WARNING = "error", "warning"

MAX_MESSAGE_WORDS = 40


@dataclass(frozen=True)
class Issue:
    code: str
    level: str
    step: str
    message: str

    def __str__(self) -> str:
        where = f"[{self.step}] " if self.step else ""
        return f"{self.level:<7} {self.code}  {where}{self.message}"


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text))


def lint(flow: Flow, max_message_words: int = MAX_MESSAGE_WORDS) -> list[Issue]:
    issues: list[Issue] = []

    def add(code: str, level: str, step: str, message: str) -> None:
        issues.append(Issue(code, level, step, message))

    # E001: the flow needs a valid starting step.
    if not flow.start:
        add("E001", ERROR, "", "The flow has no 'start' step")
    elif flow.start not in flow.steps:
        add("E001", ERROR, "", f"The start step '{flow.start}' does not exist")

    for step_id, step in flow.steps.items():
        kind = step.get("type")

        # E002: every step needs a known type.
        if kind not in STEP_TYPES:
            known = ", ".join(sorted(STEP_TYPES))
            add("E002", ERROR, step_id, f"Unknown step type '{kind}'. Use one of: {known}")
            continue

        # E003: every link must point at a step that exists.
        for label, target in flow.targets(step_id):
            if target not in flow.steps:
                add("E003", ERROR, step_id, f"'{label}' points to '{target}', which does not exist")

        # E004: a step that is not an ending must lead somewhere.
        if kind not in FINAL_TYPES and not step.get("next") and not step.get("options"):
            add("E004", ERROR, step_id, "Dead end: the conversation stops here with no ending")

        # W001: every step should say something.
        say = str(step.get("say") or "")
        if not say.strip():
            add("W001", WARNING, step_id, "The step has no 'say' text")
        elif _word_count(say) > max_message_words:
            add("W002", WARNING, step_id,
                f"The message is {_word_count(say)} words. Aim for {max_message_words} or fewer")

        if kind == "question":
            no_match = step.get("no_match")

            # E005: a question must say what happens when the answer is not understood.
            if not no_match:
                add("E005", ERROR, step_id, "The question has no 'no_match' reply for unclear answers")
            # E006: retries must end somewhere, or the user is stuck in a loop.
            elif not no_match.get("then"):
                add("E006", ERROR, step_id,
                    "'no_match' has no 'then' step, so the user can be asked again forever")

            # W003: ask one thing at a time.
            if say.count("?") > 1:
                add("W003", WARNING, step_id, "The step asks more than one question")

            # W004: a free text question should say what a good answer looks like.
            if not step.get("options") and not step.get("pattern"):
                add("W004", WARNING, step_id,
                    "Free text question with no 'pattern', so any answer is accepted")

    if flow.start in flow.steps:
        reachable = flow.reachable_from(flow.start)

        # E007: every step should be reachable from the start.
        for step_id in flow.steps:
            if step_id not in reachable:
                add("E007", ERROR, step_id, "No path leads to this step")

        # E008: from every step the user must be able to reach an ending.
        for step_id in sorted(reachable):
            if flow.step_type(step_id) not in STEP_TYPES:
                continue
            ahead = flow.reachable_from(step_id)
            if not any(flow.step_type(s) in FINAL_TYPES for s in ahead):
                add("E008", ERROR, step_id, "Trap: no ending can be reached from this step")

        # W005: there should be a way to reach a person.
        if not any(flow.step_type(s) == "handover" for s in reachable):
            add("W005", WARNING, "", "No handover step can be reached, so users cannot get to a person")

    order = {step_id: i for i, step_id in enumerate(flow.steps)}
    return sorted(issues, key=lambda i: (i.level != ERROR, order.get(i.step, -1), i.code))


def has_errors(issues: list[Issue]) -> bool:
    return any(issue.level == ERROR for issue in issues)
