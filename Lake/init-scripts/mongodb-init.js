// BioNexus MongoDB Initialization Script
// Sets up collections and indexes for flexible document storage

const database = db.getSiblingDB('bionexus');

function ensureCollection(name, options) {
  const existing = database.getCollectionNames();
  if (!existing.includes(name)) {
    database.createCollection(name, options);
  }
}

// Create collections
ensureCollection('raw_ingestions', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['source', 'data_type', 'timestamp'],
      properties: {
        source: { bsonType: 'string', description: 'Data source identifier' },
        data_type: { bsonType: 'string', description: 'Type of biological data' },
        timestamp: { bsonType: 'date', description: 'Ingestion timestamp' },
        raw_data: { bsonType: 'object', description: 'Raw ingested data' },
        batch_id: { bsonType: 'string' },
        processed: { bsonType: 'bool' }
      }
    }
  }
});

ensureCollection('ingestion_metadata', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['source_id', 'batch_id'],
      properties: {
        source_id: { bsonType: 'string' },
        batch_id: { bsonType: 'string' },
        record_count: { bsonType: 'int' },
        start_time: { bsonType: 'date' },
        end_time: { bsonType: 'date' },
        status: { enum: ['pending', 'processing', 'completed', 'failed'] },
        error_log: { bsonType: 'array' }
      }
    }
  }
});

ensureCollection('data_lineage', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['object_id', 'source'],
      properties: {
        object_id: { bsonType: 'string' },
        source: { bsonType: 'string' },
        transformations: { bsonType: 'array' },
        parent_ids: { bsonType: 'array' },
        created_at: { bsonType: 'date' }
      }
    }
  }
});

ensureCollection('api_responses_cache', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['endpoint', 'query_hash'],
      properties: {
        endpoint: { bsonType: 'string' },
        query_hash: { bsonType: 'string' },
        response_data: { bsonType: 'object' },
        status_code: { bsonType: 'int' },
        retrieved_at: { bsonType: 'date' },
        expires_at: { bsonType: 'date' }
      }
    }
  }
});

// Create indexes for performance
database.raw_ingestions.createIndex({ source: 1, timestamp: -1 });
database.raw_ingestions.createIndex({ batch_id: 1 });
database.raw_ingestions.createIndex({ processed: 1 });
database.raw_ingestions.createIndex({ timestamp: 1 }, { expireAfterSeconds: 2592000 }); // 30 days TTL

database.ingestion_metadata.createIndex({ source_id: 1, batch_id: 1 }, { unique: true });
database.ingestion_metadata.createIndex({ status: 1 });
database.ingestion_metadata.createIndex({ start_time: -1 });

database.data_lineage.createIndex({ object_id: 1 });
database.data_lineage.createIndex({ source: 1 });
database.data_lineage.createIndex({ parent_ids: 1 });

database.api_responses_cache.createIndex({ endpoint: 1, query_hash: 1 }, { unique: true });
database.api_responses_cache.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 }); // TTL index

// Create users and roles (idempotent)
const user = database.getUser('bionexus_user');
const roles = [
  { role: 'readWrite', db: 'bionexus' },
  { role: 'dbAdmin', db: 'bionexus' }
];

if (!user) {
  database.createUser({
    user: 'bionexus_user',
    pwd: process.env.MONGODB_PASSWORD || 'bionexus_dev_password',
    roles
  });
} else {
  database.updateUser('bionexus_user', { roles });
}
