from triage.complexity import measure


def test_llm_stack_has_more_code_than_vega():
    report = measure()
    data = report.to_json()
    assert data["delta_code_lines_llm_minus_vega"] > 0


def test_fair_delta_excludes_http_and_still_positive_for_freeform():
    data = measure().to_json()
    fair = data["fair_deltas"]
    assert fair["http_client_code_lines"] > 0
    assert fair["parse_repair_code_lines"] > 0
    assert fair["llm_freeform_semantic_minus_vega"] > 0
    # Structured shrinks vs freeform semantic delta but stays above Vega core.
    assert fair["llm_structured_semantic_minus_vega"] > 0
    assert (
        fair["llm_structured_semantic_minus_vega"]
        < fair["llm_freeform_semantic_minus_vega"]
    )


def test_prompt_chars_reported():
    chars = measure().prompt_chars
    assert chars["llm_system_prompt"] > 100
    assert chars["vega_criteria_and_instructions"] > 50
