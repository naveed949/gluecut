from pathlib import Path

from triage.eval import load_fixtures, run_eval


def test_glue_fixture_excluded_from_accuracy_denominator():
    fixtures = load_fixtures()
    glue = [r for r in fixtures if r.get("eval", {}).get("accuracy") is False]
    assert any(r["id"] == "broken-json-marker" for r in glue)

    report = run_eval("llm")
    assert report.n_glue_only >= 1
    assert report.n_scored == report.n - report.n_glue_only
    assert Path("fixtures/tickets.jsonl").exists()
