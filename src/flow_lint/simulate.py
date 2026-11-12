"""Walk through a flow with a list of user answers and record the transcript."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .model import FINAL_TYPES, Flow

MAX_TURNS = 200


@dataclass
class Transcript:
    turns: list[tuple[str, str]] = field(default_factory=list)
    path: list[str] = field(default_factory=list)
    captured: dict[str, str] = field(default_factory=dict)
    outcome: str = "incomplete"

    def as_text(self) -> str:
        width = 5
        lines = [f"{speaker.upper():<{width}} {text}" for speaker, text in self.turns]
        lines.append(f"[{self.outcome}]")
        return "\n".join(lines)


def _fill(text: str, captured: dict[str, str]) -> str:
    """Replace {name} in a message with what the user said earlier."""
    return re.sub(r"\{(\w+)\}", lambda m: captured.get(m.group(1), m.group(0)), text)


def _matches_option(answer: str, option: dict) -> bool:
    low = answer.lower()
    for keyword in option.get("match") or []:
        if re.search(rf"\b{re.escape(str(keyword).lower())}\b", low):
            return True
    return False


def simulate(flow: Flow, answers: list[str]) -> Transcript:
    """Run the flow. Each question takes the next answer from the list."""
    transcript = Transcript()
    queue = list(answers)
    current = flow.start
    retries: dict[str, int] = {}

    for _ in range(MAX_TURNS):
        if current not in flow.steps:
            transcript.outcome = f"broken: step '{current}' does not exist"
            return transcript
        step = flow.steps[current]
        kind = step.get("type")
        transcript.path.append(current)
        say = _fill(str(step.get("say") or ""), transcript.captured)
        if say and not retries.get(current):
            transcript.turns.append(("bot", say.strip()))

        if kind in FINAL_TYPES:
            transcript.outcome = "handover" if kind == "handover" else "completed"
            return transcript

        if kind == "message":
            if not step.get("next"):
                transcript.outcome = f"broken: dead end at '{current}'"
                return transcript
            current = str(step["next"])
            continue

        # A question: take the next answer.
        if not queue:
            transcript.outcome = f"abandoned at '{current}'"
            return transcript
        answer = queue.pop(0)
        transcript.turns.append(("user", answer))

        target = None
        options = step.get("options") or []
        if options:
            for option in options:
                if _matches_option(answer, option):
                    target = option.get("next")
                    break
        else:
            pattern = step.get("pattern")
            if not pattern or re.fullmatch(str(pattern), answer.strip(), flags=re.IGNORECASE):
                target = step.get("next")
                if step.get("capture"):
                    transcript.captured[str(step["capture"])] = answer.strip()

        if target:
            retries.pop(current, None)
            current = str(target)
            continue

        # The answer was not understood.
        no_match = step.get("no_match") or {}
        retries[current] = retries.get(current, 0) + 1
        if retries[current] > int(no_match.get("max_retries", 1)):
            if not no_match.get("then"):
                transcript.outcome = f"broken: stuck at '{current}'"
                return transcript
            retries.pop(current, None)
            current = str(no_match["then"])
            continue
        transcript.turns.append(("bot", _fill(str(no_match.get("say") or say), transcript.captured).strip()))

    transcript.outcome = "broken: too many turns"
    return transcript
