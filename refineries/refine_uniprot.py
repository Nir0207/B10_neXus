"""
Polars refinery for UniProt raw JSON  (Bronze → Silver).

Reads every *.json file in RAW_UNIPROT_DIR, extracts canonical protein /
gene fields, maps embedded Reactome cross-references, and writes three
Silver-layer CSV artefacts:

    silver_proteins.csv        – one row per UniProt entry
    silver_gene_symbol_map.csv – Gene Symbol → UniProt ID lookup
    silver_reactome_map.csv    – UniProt ID → Reactome Pathway mapping

All three CSVs are designed for direct COPY / upsert into Postgres.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import polars as pl

from config import RAW_UNIPROT_DIR, SILVER_CSV_DIR
from idempotency import filter_unprocessed, mark_processed_many

logger = logging.getLogger(__name__)

PROTEIN_SCHEMA: dict[str, pl.DataType] = {
    "uniprot_id": pl.Utf8,
    "uniprot_kb_id": pl.Utf8,
    "hgnc_symbol": pl.Utf8,
    "gene_synonyms": pl.Utf8,
    "protein_name": pl.Utf8,
    "organism": pl.Utf8,
    "sequence_length": pl.Int64,
    "molecular_weight": pl.Int64,
    "annotation_score": pl.Float64,
    "sequence": pl.Utf8,
    "data_source": pl.Utf8,
}

GENE_MAP_SCHEMA: dict[str, pl.DataType] = {
    "uniprot_id": pl.Utf8,
    "hgnc_symbol": pl.Utf8,
    "source_file": pl.Utf8,
}

REACTOME_SCHEMA: dict[str, pl.DataType] = {
    "uniprot_id": pl.Utf8,
    "reactome_id": pl.Utf8,
    "pathway_name": pl.Utf8,
}


# ── Field extraction helpers ─────────────────────────────────────────────────

def _extract_record(entry: dict[str, Any]) -> dict[str, Any]:
    """Flatten one UniProt result entry into a single-row dict."""
    genes: list[dict] = entry.get("genes", [])
    first_gene: dict = genes[0] if genes else {}

    hgnc_symbol: str = first_gene.get("geneName", {}).get("value", "")
    synonyms: list[str] = [
        s["value"]
        for s in first_gene.get("synonyms", [])
        if isinstance(s.get("value"), str)
    ]

    protein_name: str = (
        entry.get("proteinDescription", {})
        .get("recommendedName", {})
        .get("fullName", {})
        .get("value", "")
    )

    seq: dict[str, Any] = entry.get("sequence", {})

    return {
        "uniprot_id": entry.get("primaryAccession", ""),
        "uniprot_kb_id": entry.get("uniProtkbId", ""),
        "hgnc_symbol": hgnc_symbol,
        "gene_synonyms": "|".join(synonyms),
        "protein_name": protein_name,
        "organism": entry.get("organism", {}).get("scientificName", ""),
        "sequence_length": seq.get("length"),
        "molecular_weight": seq.get("molWeight"),
        "annotation_score": entry.get("annotationScore"),
        "sequence": seq.get("value", ""),
        "data_source": "UniProt",
    }


def _extract_reactome_mappings(
    uniprot_id: str,
    entry: dict[str, Any],
) -> list[dict[str, str]]:
    """Pull Reactome pathway rows from UniProtKB cross-references."""
    rows: list[dict[str, str]] = []
    for xref in entry.get("uniProtKBCrossReferences", []):
        if xref.get("database") != "Reactome":
            continue
        pathway_name: str = next(
            (
                p["value"]
                for p in xref.get("properties", [])
                if p.get("key") == "PathwayName"
            ),
            "",
        )
        rows.append(
            {
                "uniprot_id": uniprot_id,
                "reactome_id": xref.get("id", ""),
                "pathway_name": pathway_name,
            }
        )
    return rows


def _read_uniprot_entries(filepath: Path) -> list[dict[str, Any]]:
    data: dict[str, Any] = json.loads(filepath.read_text(encoding="utf-8"))
    results = data.get("results", [])
    if not isinstance(results, list):
        raise ValueError(f"Unexpected UniProt payload shape in {filepath}")
    return results


def _validate_uniprot_integrity(proteins_df: pl.DataFrame) -> pl.DataFrame:
    if proteins_df.is_empty():
        raise ValueError("No protein records extracted — check raw JSON format.")

    missing_keys = proteins_df.filter(pl.col("uniprot_id").str.strip_chars() == "")
    if not missing_keys.is_empty():
        raise ValueError("Encountered UniProt records without primary accession.")

    duplicate_keys = proteins_df.group_by("uniprot_id").len().filter(pl.col("len") > 1)
    if not duplicate_keys.is_empty():
        duplicates = duplicate_keys["uniprot_id"].to_list()
        logger.warning(
            "Duplicate UniProt primary keys detected in raw lake snapshot; keeping the last record for %s",
            duplicates,
        )

    return proteins_df.unique(subset=["uniprot_id"], keep="last")


# ── Public refinery entry point ───────────────────────────────────────────────

def refine_uniprot(
    raw_dir: Path = RAW_UNIPROT_DIR,
    out_dir: Path = SILVER_CSV_DIR,
    *,
    skip_processed: bool = True,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """
    Read raw UniProt JSON → return (proteins_df, gene_map_df, reactome_df).

    Side-effects
    ------------
    - Writes three CSV files to *out_dir*.
    - Updates the idempotency manifest for each processed file.

    Returns
    -------
    Tuple of three DataFrames so callers can inspect or test results without
    touching the filesystem.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    json_files = sorted(raw_dir.rglob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {raw_dir}")

    to_process = filter_unprocessed(json_files) if skip_processed else json_files

    if skip_processed and not to_process:
        logger.info("All UniProt files already processed; loading existing CSVs.")
        return (
            pl.read_csv(out_dir / "silver_proteins.csv"),
            pl.read_csv(out_dir / "silver_gene_symbol_map.csv"),
            pl.read_csv(out_dir / "silver_reactome_map.csv"),
        )
    if skip_processed:
        logger.info(
            "Detected %d/%d changed UniProt files; rebuilding full Silver snapshot.",
            len(to_process),
            len(json_files),
        )

    proteins: list[dict[str, Any]] = []
    gene_maps: list[dict[str, str]] = []
    reactome_maps: list[dict[str, str]] = []

    for filepath in json_files:
        logger.info("Refining %s", filepath.name)
        for entry in _read_uniprot_entries(filepath):
            rec = _extract_record(entry)
            proteins.append(rec)
            if rec["hgnc_symbol"]:
                gene_maps.append(
                    {
                        "uniprot_id": rec["uniprot_id"],
                        "hgnc_symbol": rec["hgnc_symbol"],
                        "source_file": filepath.relative_to(raw_dir).as_posix(),
                    }
                )
            reactome_maps.extend(
                _extract_reactome_mappings(rec["uniprot_id"], entry)
            )

    proteins_df = _validate_uniprot_integrity(pl.from_dicts(proteins, schema=PROTEIN_SCHEMA))
    gene_map_df = (
        pl.from_dicts(gene_maps, schema=GENE_MAP_SCHEMA)
        .unique(subset=["uniprot_id", "hgnc_symbol"], keep="last")
        .sort(["hgnc_symbol", "uniprot_id"])
    )
    reactome_df = (
        pl.from_dicts(reactome_maps, schema=REACTOME_SCHEMA)
        .unique(subset=["uniprot_id", "reactome_id"], keep="last")
        .sort(["uniprot_id", "reactome_id"])
        if reactome_maps
        else pl.DataFrame(
            {"uniprot_id": [], "reactome_id": [], "pathway_name": []},
            schema=REACTOME_SCHEMA,
        )
    )

    proteins_df = proteins_df.sort("uniprot_id")
    proteins_df.write_csv(out_dir / "silver_proteins.csv")
    gene_map_df.write_csv(out_dir / "silver_gene_symbol_map.csv")
    reactome_df.write_csv(out_dir / "silver_reactome_map.csv")

    if skip_processed and to_process:
        mark_processed_many(to_process)

    logger.info(
        "Wrote %d proteins | %d gene-map rows | %d reactome pathway rows",
        len(proteins_df),
        len(gene_map_df),
        len(reactome_df),
    )
    return proteins_df, gene_map_df, reactome_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p, g, r = refine_uniprot(skip_processed=True)
    print(f"proteins={len(p)}  gene_map={len(g)}  reactome={len(r)}")
