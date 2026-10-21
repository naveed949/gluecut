from pathlib import Path

from triage.eval import DEV_FIXTURES, load_fixtures, run_eval


def test_glue_fixture_excluded_from_accuracy_denominator():
    fixtures = load_fixtures(DEV_FIXTURES)
    glue = [r for r in fixtures if r.get("eval", {}).get("accuracy") is False]
    assert any(r["id"] == "broken-json-marker" for r in glue)

    report = run_eval("llm", DEV_FIXTURES)
    assert report.n_glue_only >= 1
    assert report.n_scored == report.n - report.n_glue_only
    assert Path("fixtures/triage/dev.jsonl").exists()


def test_held_out_default_is_large():
    fixtures = load_fixtures()
    assert len(fixtures) >= 100
