from pathlib import Path

from flow_lint.cli import main
from flow_lint.diagram import to_mermaid
from flow_lint.model import load_flow, parse_flow
from flow_lint.simulate import simulate

EXAMPLES = Path(__file__).parent.parent / "examples"


def flow():
    return load_flow(EXAMPLES / "update_address.yaml")


def test_happy_path_completes_and_repeats_details_back():
    result = simulate(flow(), ["yes", "SR2 7AB", "12 High Street", "yes"])
    assert result.outcome == "completed"
    assert result.captured == {"postcode": "SR2 7AB", "first_line": "12 High Street"}
    assert ("bot", "Your new address starts 12 High Street, SR2 7AB. Is that right?") in result.turns


def test_bad_postcode_gets_a_helpful_retry_then_carries_on():
    result = simulate(flow(), ["yes", "my postcode", "SR2 7AB", "12 High Street", "yes"])
    assert result.outcome == "completed"
    assert any("does not look like a UK postcode" in text for _, text in result.turns)


def test_repeated_unclear_answers_go_to_a_person():
    result = simulate(flow(), ["maybe", "what"])
    assert result.outcome == "handover"
    assert result.path[-1] == "handover"


def test_user_can_correct_the_address():
    answers = ["yes", "SR2 7AB", "12 High Street", "no", "NE1 4ST", "3 Low Road", "yes"]
    result = simulate(flow(), answers)
    assert result.outcome == "completed"
    assert result.captured["postcode"] == "NE1 4ST"


def test_running_out_of_answers_is_recorded_as_abandoned():
    result = simulate(flow(), ["yes"])
    assert result.outcome == "abandoned at 'ask_postcode'"


def test_not_signed_in_ends_politely():
    assert simulate(flow(), ["no"]).outcome == "completed"


def test_bare_yaml_yes_and_no_are_read_as_words():
    parsed = parse_flow({
        "start": "q",
        "steps": {
            "q": {"type": "question", "say": "OK?",
                  "options": [{"match": [True], "next": "e"}],
                  "no_match": {"then": "e"}},
            "e": {"type": "end", "say": "Bye."},
        },
    })
    assert parsed.steps["q"]["options"][0]["match"] == ["yes"]


def test_keyword_must_be_a_whole_word():
    # "no" must not match inside "know".
    result = simulate(flow(), ["I do not know", "yes", "SR2 7AB", "12 High Street", "yes"])
    assert result.turns[2] == ("user", "I do not know")
    assert result.path[2] == "sign_in_first"


def test_diagram_has_every_step_and_labelled_links():
    text = to_mermaid(flow())
    assert text.startswith("flowchart TD")
    assert "ask_signed_in -- yes --> ask_postcode" in text
    assert "confirm -. no match .-> handover" in text


def test_cli_exit_codes(capsys):
    assert main(["check", str(EXAMPLES / "update_address.yaml")]) == 0
    assert main(["check", str(EXAMPLES / "broken_flow.yaml")]) == 1
    capsys.readouterr()
