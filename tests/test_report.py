from triage.report import render_html, render_markdown


def test_render_markdown_table_has_engines_and_metrics():
    complexity = {
        "core_triage_by_engine": {"vega": 47, "llm": 80, "llm_structured": 85},
        "fair_deltas": {
            "llm_freeform_semantic_minus_vega": 46,
            "llm_structured_semantic_minus_vega": 38,
            "parse_repair_code_lines": 13,
            "http_client_code_lines": 53,
        },
        "prompt_chars": {
            "llm_system_prompt": 657,
            "vega_criteria_and_instructions": 560,
        },
    }
    base = {
        "n": 18,
        "n_scored": 17,
        "team_accuracy": 0.765,
        "priority_accuracy": 0.5,
        "needs_human_accuracy": 0.5,
        "forced_wrong_team_rate": 0.0,
        "needs_review_rate": 0.4,
        "abstain_rate": 0.1,
        "mean_parse_attempts": 0.0,
        "mean_repair_rounds": 0.0,
        "cases": [],
    }
    evals = {
        "vega": {**base, "mean_parse_attempts": 0.0},
        "llm": {**base, "mean_parse_attempts": 1.0},
        "llm_structured": {**base, "mean_parse_attempts": 1.0},
    }
    md = render_markdown(
        complexity=complexity,
        evals=evals,
        engines=("vega", "llm", "llm_structured"),
        fixtures="fixtures/tickets.jsonl",
        generated_at="2026-10-19 00:00 UTC",
    )
    assert "| Metric | vega | llm | llm_structured |" in md
    assert "Team accuracy" in md
    assert "Fair delta vs Vega" in md
    assert "+46" in md
    assert "+38" in md


def test_render_html_embeds_markdown():
    md = "| Metric | vega |\n|--------|------|\n| Team accuracy | 76.5% |\n"
    doc = render_html(md)
    assert "<table>" in doc or "tableLines" in doc
    assert "gluecut" in doc
