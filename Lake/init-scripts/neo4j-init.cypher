// BioNexus Neo4j Initialization Script
// Creates foundational knowledge graph schema for biological networks

// Create constraints and indexes (Neo4j 5 syntax)
CREATE CONSTRAINT gene_uniqueness IF NOT EXISTS FOR (g:Gene) REQUIRE g.hgnc_symbol IS UNIQUE;
CREATE CONSTRAINT protein_uniqueness IF NOT EXISTS FOR (p:Protein) REQUIRE p.uniprot_accession IS UNIQUE;
CREATE CONSTRAINT disease_uniqueness IF NOT EXISTS FOR (d:Disease) REQUIRE d.mondo_id IS UNIQUE;
CREATE CONSTRAINT compound_uniqueness IF NOT EXISTS FOR (c:Compound) REQUIRE c.chembl_id IS UNIQUE;

// Create indexes for common queries
CREATE INDEX gene_name_idx IF NOT EXISTS FOR (g:Gene) ON (g.name);
CREATE INDEX protein_name_idx IF NOT EXISTS FOR (p:Protein) ON (p.name);
CREATE INDEX disease_name_idx IF NOT EXISTS FOR (d:Disease) ON (d.name);
CREATE INDEX compound_name_idx IF NOT EXISTS FOR (c:Compound) ON (c.name);

// Create relationship indexes
CREATE INDEX encodes_idx IF NOT EXISTS FOR ()-[r:ENCODES]-() ON (r.confidence);
CREATE INDEX targets_idx IF NOT EXISTS FOR ()-[r:TARGETS]-() ON (r.evidence_count);
CREATE INDEX associated_with_idx IF NOT EXISTS FOR ()-[r:ASSOCIATED_WITH]-() ON (r.p_value);

// Initialize root reference nodes
MERGE (kg:KnowledgeGraph {name: "BioNexus Master Graph", version: "1.0", created: timestamp()});

// Create sample ontology nodes for reference
MERGE (humans:Organism {name: "Homo sapiens", taxonomy_id: 9606});
MERGE (kg)-[:REFERENCES]->(humans);

// Create biological relationship type definitions
MERGE (rel_encodes:RelationType {name: "ENCODES", description: "Gene encodes Protein"});
MERGE (rel_targets:RelationType {name: "TARGETS", description: "Compound targets Protein"});
MERGE (rel_assoc:RelationType {name: "ASSOCIATED_WITH", description: "Gene/Protein associated with Disease"});
MERGE (rel_ppi:RelationType {name: "INTERACTS_WITH", description: "Protein-Protein Interaction"});

MERGE (kg)-[:DEFINES]->(rel_encodes);
MERGE (kg)-[:DEFINES]->(rel_targets);
MERGE (kg)-[:DEFINES]->(rel_assoc);
MERGE (kg)-[:DEFINES]->(rel_ppi);
