from __future__ import annotations

import asyncio
import argparse
import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ops.ops_logger import configure_logging

from disease_programs import DEFAULT_DISEASE_PROGRAMS, DiseaseProgram
from ncbi import NCBIGatherer
from opentargets import OpenTargetsGatherer
from uniprot import UniProtGatherer

configure_logging(service_name="gatherers")
logger = logging.getLogger(__name__)


async def gather_disease_program(
    program: DiseaseProgram,
    *,
    uniprot: UniProtGatherer,
    opentargets: OpenTargetsGatherer,
    ncbi: NCBIGatherer,
) -> list[str]:
    disease_id = program.disease_id
    if disease_id is None:
        disease_id, resolved_name = await opentargets.resolve_disease_id(program.disease_query)
        logger.info("Resolved disease '%s' to %s (%s)", program.disease_query, disease_id, resolved_name)

    payload = await opentargets.fetch_disease_evidence(
        disease_id,
        organ=program.organ,
        stem=f"{disease_id}_evidence",
    )
    target_genes = opentargets.extract_top_target_genes(payload, limit=program.max_targets)
    if not target_genes:
        raise RuntimeError(f"No target genes returned for {program.disease_query} ({disease_id})")

    logger.info(
        "Fetching downstream sources for %s (%s): %s",
        program.disease_query,
        disease_id,
        ", ".join(target_genes),
    )

    await asyncio.gather(
        *(uniprot.fetch(gene, organism=program.organ) for gene in target_genes),
        *(ncbi.fetch_geo_studies(gene, organ=program.organ, max_records=program.max_studies_per_gene) for gene in target_genes),
    )
    return target_genes


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BioNexus gatherer orchestrator")
    parser.add_argument("--disease-id", default=None)
    parser.add_argument("--disease-name", default=None)
    parser.add_argument("--organ", default="brain")
    parser.add_argument("--max-targets", type=int, default=6)
    parser.add_argument("--max-studies-per-gene", type=int, default=20)
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    uniprot = UniProtGatherer()
    opentargets = OpenTargetsGatherer()
    ncbi = NCBIGatherer()

    if args.disease_id or args.disease_name:
        if not args.disease_name and not args.disease_id:
            raise SystemExit("Provide either --disease-name or --disease-id.")
        disease_query = args.disease_name or args.disease_id
        programs = (
            DiseaseProgram(
                disease_query=disease_query,
                disease_id=args.disease_id,
                organ=args.organ,
                max_targets=args.max_targets,
                max_studies_per_gene=args.max_studies_per_gene,
            ),
        )
    else:
        programs = DEFAULT_DISEASE_PROGRAMS

    for program in programs:
        await gather_disease_program(
            program,
            uniprot=uniprot,
            opentargets=opentargets,
            ncbi=ncbi,
        )


if __name__ == "__main__":
    asyncio.run(main())
