import asyncio
from uniprot import UniProtGatherer
from opentargets import OpenTargetsGatherer
from ncbi import NCBIGatherer

async def main():
    print("Starting BioNexus Gatherers...")
    
    # Initialize gatherers
    # Using the project root relative paths so it populates the local Lake correctly.
    uniprot = UniProtGatherer(base_dir="../Lake/data_lake/raw/uniprot")
    opentargets = OpenTargetsGatherer(base_dir="../Lake/data_lake/raw/opentargets")
    ncbi = NCBIGatherer(base_dir="../Lake/data_lake/raw/ncbi")
    
    # We will gather a few sample targets to demonstrate functionality
    sample_genes = ["BRCA1", "EGFR"]
    
    print("\n--- Running UniProt Gatherer ---")
    for gene in sample_genes:
        await uniprot.fetch(gene)
    
    print("\n--- Running Open Targets Gatherer ---")
    # Fetch Target-Disease Evidence for Liver Disease (EFO_0000572)
    await opentargets.fetch_liver_evidence("EFO_0000572")
    
    print("\n--- Running NCBI Gatherer ---")
    for gene in sample_genes:
        await ncbi.fetch_geo_studies(gene)
        
    print("\nDone! Data has been populated into the local Lake.")

if __name__ == "__main__":
    asyncio.run(main())
