"""
Shared test stubs — realistic but minimal UniProt and NCBI GEO payloads.

Import these constants directly from tests (not via a fixture) so that
helper functions under test can be called with plain dicts.
"""
from __future__ import annotations

# ── UniProt stub ──────────────────────────────────────────────────────────────

BRCA1_RECORD: dict = {
    "primaryAccession": "P38398",
    "uniProtkbId": "BRCA1_HUMAN",
    "annotationScore": 5.0,
    "organism": {"scientificName": "Homo sapiens"},
    "proteinDescription": {
        "recommendedName": {
            "fullName": {"value": "Breast cancer type 1 susceptibility protein"}
        }
    },
    "genes": [
        {
            "geneName": {"value": "BRCA1"},
            "synonyms": [{"value": "RNF53"}],
        }
    ],
    "sequence": {
        "value": "MDLSALRVEEV",
        "length": 1863,
        "molWeight": 207721,
        "crc64": "ABC123",
        "md5": "DEF456",
    },
    "uniProtKBCrossReferences": [
        {
            "database": "Reactome",
            "id": "R-HSA-1221632",
            "properties": [{"key": "PathwayName", "value": "Meiotic synapsis"}],
        },
        {
            "database": "Reactome",
            "id": "R-HSA-3108214",
            "properties": [
                {
                    "key": "PathwayName",
                    "value": "SUMOylation of DNA damage response and repair proteins",
                }
            ],
        },
        # Non-Reactome xref — must be ignored by the mapper
        {
            "database": "STRING",
            "id": "9606.ENSP00000350283",
            "properties": [],
        },
    ],
}

EGFR_RECORD: dict = {
    "primaryAccession": "P00533",
    "uniProtkbId": "EGFR_HUMAN",
    "annotationScore": 5.0,
    "organism": {"scientificName": "Homo sapiens"},
    "proteinDescription": {
        "recommendedName": {
            "fullName": {"value": "Epidermal growth factor receptor"}
        }
    },
    "genes": [{"geneName": {"value": "EGFR"}, "synonyms": []}],
    "sequence": {
        "value": "MRPSGTAGAALLALLAALCPASRALEEKKVC",
        "length": 1210,
        "molWeight": 134277,
        "crc64": "XYZ",
        "md5": "QRS",
    },
    "uniProtKBCrossReferences": [],
}

BRCA1_STUB: dict = {"results": [BRCA1_RECORD]}
EGFR_STUB: dict = {"results": [EGFR_RECORD]}
BOTH_STUB: dict = {"results": [BRCA1_RECORD, EGFR_RECORD]}


# ── NCBI GEO stub ─────────────────────────────────────────────────────────────

NCBI_STUB: dict = {
    "header": {"type": "esummary", "version": "0.3"},
    "result": {
        "uids": ["200267911", "200307271"],
        "200267911": {
            "uid": "200267911",
            "accession": "GSE267911",
            "title": "KAT2B-Mediated Epigenetic Suppression",
            "summary": "Summary text.",
            "gpl": "15433",
            "gse": "267911",
            "taxon": "Homo sapiens",
            "entrytype": "GSE",
            "gdstype": "Expression profiling by high throughput sequencing",
            "pdat": "2026/03/18",
            "samples": [{"accession": "GSM8281485", "title": "RKO-DMSO-rep-1"}],
        },
        "200307271": {
            "uid": "200307271",
            "accession": "GSE307271",
            "title": "Another Study",
            "summary": "Another summary.",
            "gpl": "20301",
            "gse": "307271",
            "taxon": "Homo sapiens",
            "entrytype": "GSE",
            "gdstype": "Expression profiling by array",
            "pdat": "2026/02/01",
            "samples": [],
        },
    },
}
