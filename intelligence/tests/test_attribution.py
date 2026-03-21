from __future__ import annotations

from bionexus_intelligence.attribution import with_data_source_attribution


def test_with_data_source_attribution_appends_block() -> None:
    result = with_data_source_attribution("Lead summary", ["Source: Open Targets"])
    assert "Lead summary" in result
    assert "Data Source Attribution:" in result
    assert "Source: Open Targets" in result


def test_with_data_source_attribution_does_not_duplicate_existing_block() -> None:
    original = "Lead summary\n\nData Source Attribution: Source: Open Targets"
    result = with_data_source_attribution(original, ["Source: NCBI GEO"])
    assert result == original
