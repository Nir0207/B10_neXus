from __future__ import annotations


def with_data_source_attribution(answer: str, sources: list[str]) -> str:
    """Append a mandatory attribution block to every generated answer."""
    normalized_sources = sorted({source.strip() for source in sources if source.strip()})
    if not normalized_sources:
        normalized_sources = ["Unknown"]

    body = answer.strip() or "No result generated."
    attribution = "; ".join(normalized_sources)

    if "Data Source Attribution:" in body:
        return body

    return f"{body}\n\nData Source Attribution: {attribution}"
