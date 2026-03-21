from __future__ import annotations

import asyncio
import logging

from ncbi import NCBIGatherer
from opentargets import OpenTargetsGatherer
from uniprot import UniProtGatherer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


async def main() -> None:
    uniprot = UniProtGatherer()
    opentargets = OpenTargetsGatherer()
    ncbi = NCBIGatherer()

    sample_genes = ["BRCA1", "EGFR"]

    for gene in sample_genes:
        await uniprot.fetch(gene, organism="liver")

    await opentargets.fetch_liver_evidence("EFO_0000572")

    for gene in sample_genes:
        await ncbi.fetch_geo_studies(gene, organ="liver")


if __name__ == "__main__":
    asyncio.run(main())
