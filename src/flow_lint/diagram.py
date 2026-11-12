"""Draw a flow as a Mermaid diagram. GitHub shows these as pictures."""

from __future__ import annotations

from .model import Flow

_SHAPES = {
    "message": ("[", "]"),
    "question": ("{{", "}}"),
    "handover": ("[/", "/]"),
    "end": ("([", "])"),
}


def _label(step_id: str, step: dict) -> str:
    text = " ".join(str(step.get("say") or step_id).split())
    if len(text) > 40:
        text = text[:37].rstrip() + "..."
    return text.replace('"', "'")


def to_mermaid(flow: Flow) -> str:
    lines = ["flowchart TD"]
    for step_id, step in flow.steps.items():
        left, right = _SHAPES.get(str(step.get("type")), ("[", "]"))
        lines.append(f'    {step_id}{left}"{_label(step_id, step)}"{right}')
    for step_id in flow.steps:
        for label, target in flow.targets(step_id):
            if target not in flow.steps:
                continue
            if label == "next":
                lines.append(f"    {step_id} --> {target}")
            elif label == "no match":
                lines.append(f"    {step_id} -. no match .-> {target}")
            else:
                lines.append(f"    {step_id} -- {label} --> {target}")
    return "\n".join(lines)
