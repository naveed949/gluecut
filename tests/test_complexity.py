from triage.complexity import measure


def test_llm_engine_has_more_code_than_vega():
    report = measure()
    assert report.files["llm"].code_lines > report.files["vega"].code_lines
    assert report.to_json()["delta_code_lines_llm_minus_vega"] > 0
