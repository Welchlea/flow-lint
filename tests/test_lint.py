from pathlib import Path

from flow_lint.lint import has_errors, lint
from flow_lint.model import load_flow, parse_flow

EXAMPLES = Path(__file__).parent.parent / "examples"


def codes(data):
    return [issue.code for issue in lint(parse_flow(data))]


def good_flow():
    return {
        "flow": "tiny",
        "start": "ask",
        "steps": {
            "ask": {
                "type": "question",
                "say": "Do you want to carry on?",
                "options": [
                    {"match": ["yes"], "next": "done"},
                    {"match": ["no"], "next": "person"},
                ],
                "no_match": {"say": "Yes or no?", "then": "person"},
            },
            "done": {"type": "end", "say": "All done."},
            "person": {"type": "handover", "say": "Passing you to the team."},
        },
    }


def test_good_flow_has_no_issues():
    assert codes(good_flow()) == []


def test_example_flow_is_clean():
    assert lint(load_flow(EXAMPLES / "update_address.yaml")) == []


def test_missing_start():
    flow = good_flow()
    flow["start"] = "nowhere"
    assert "E001" in codes(flow)


def test_unknown_step_type():
    flow = good_flow()
    flow["steps"]["done"]["type"] = "finish"
    assert "E002" in codes(flow)


def test_link_to_missing_step():
    flow = good_flow()
    flow["steps"]["ask"]["options"][0]["next"] = "missing"
    assert "E003" in codes(flow)


def test_dead_end():
    flow = good_flow()
    flow["steps"]["done"] = {"type": "message", "say": "Saved."}
    assert "E004" in codes(flow)


def test_question_without_no_match():
    flow = good_flow()
    del flow["steps"]["ask"]["no_match"]
    assert "E005" in codes(flow)


def test_no_match_without_a_way_out():
    flow = good_flow()
    flow["steps"]["ask"]["no_match"] = {"say": "Yes or no?"}
    assert "E006" in codes(flow)


def test_unreachable_step():
    flow = good_flow()
    flow["steps"]["orphan"] = {"type": "end", "say": "Bye."}
    assert "E007" in codes(flow)


def test_trap_loop():
    flow = {
        "flow": "loop",
        "start": "a",
        "steps": {
            "a": {"type": "message", "say": "One.", "next": "b"},
            "b": {"type": "message", "say": "Two.", "next": "a"},
        },
    }
    assert codes(flow).count("E008") == 2


def test_warnings_for_wording():
    flow = good_flow()
    flow["steps"]["ask"]["say"] = "Are you ready? Do you have your details?"
    flow["steps"]["done"]["say"] = "word " * 50
    found = codes(flow)
    assert "W003" in found and "W002" in found


def test_no_handover_is_a_warning_not_an_error():
    flow = good_flow()
    flow["steps"]["person"]["type"] = "end"
    issues = lint(parse_flow(flow))
    assert [i.code for i in issues] == ["W005"]
    assert not has_errors(issues)


def test_broken_example_finds_every_error_type():
    found = {i.code for i in lint(load_flow(EXAMPLES / "broken_flow.yaml"))}
    assert {"E003", "E004", "E005", "E006", "E007", "E008", "W003", "W004", "W005"} <= found
