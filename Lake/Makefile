.PHONY: help up down logs restart clean health init lake-init db-init test deps status pull build postgres-shell neo4j-shell mongo-shell duckdb-shell

COMPOSE ?= $(shell if command -v docker-compose >/dev/null 2>&1; then echo docker-compose; else echo "docker compose"; fi)

help:
	@echo "🧬 BioNexus Docker & Lake Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Core Commands:"
	@echo "  up              Start all services (Refinery, Postgres, Neo4j, MongoDB)"
	@echo "  down            Stop all services"
	@echo "  restart         Restart all services"
	@echo "  logs            View logs from all services"
	@echo "  health          Check health of all services"
	@echo ""
	@echo "Installation:"
	@echo "  deps            Install Python dependencies"
	@echo "  lake-init       Initialize DuckDB lake"
	@echo "  db-init         Re-run database init scripts"
	@echo "  init            Full initialization (deps + services + lake)"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean           Stop and remove volumes (⚠️  DATA LOSS)"
	@echo "  test            Run connection tests"
	@echo ""
	@echo "Service-specific:"
	@echo "  postgres-shell  Connect to Postgres"
	@echo "  neo4j-shell     Connect to Neo4j Cypher Shell"
	@echo "  mongo-shell     Connect to MongoDB"
	@echo "  duckdb-shell    Open DuckDB interactive shell"

# Core Operations
up:
	@echo "🚀 Starting services..."
	$(COMPOSE) up -d
	@sleep 5
	@make health

down:
	@echo "🛑 Stopping services..."
	$(COMPOSE) down

restart:
	@echo "🔄 Restarting services..."
	$(COMPOSE) restart
	@sleep 5
	@make health

logs:
	$(COMPOSE) logs -f

# Installation
deps:
	@echo "📦 Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "✓ Dependencies installed"

lake-init: deps
	@echo "🦆 Initializing DuckDB lake..."
	python3 scripts/duckdb_lake_init.py
	@echo "✓ Lake initialized"

db-init:
	@echo "🗄️  Reinitializing databases..."
	$(COMPOSE) exec postgres psql -U bionexus_user -d bionexus -f /docker-entrypoint-initdb.d/01-init.sql
	$(COMPOSE) exec neo4j bin/cypher-shell -u neo4j -p bionexus_dev_password < init-scripts/neo4j-init.cypher
	@echo "✓ Databases reinitialized"

init: up deps lake-init db-init
	@echo ""
	@echo "✅ Full initialization complete!"
	@echo ""
	@make health

# Health & Status
health:
	@echo "🏥 Health Check:"
	@echo ""
	@$(COMPOSE) ps --format "table {{.Service}}\t{{.Image}}\t{{.Status}}"
	@echo ""
	@echo "Testing connections..."
	@$(MAKE) test

test:
	@echo "Testing Postgres..."
	@$(COMPOSE) exec -T postgres pg_isready -U bionexus_user -d bionexus && echo "  ✓ Postgres OK" || echo "  ✗ Postgres FAILED"
	@echo ""
	@echo "Testing Neo4j..."
	@curl -s http://localhost:7474/db/neo4j/label/ > /dev/null && echo "  ✓ Neo4j OK" || echo "  ✗ Neo4j FAILED"
	@echo ""
	@echo "Testing MongoDB..."
	@$(COMPOSE) exec -T mongodb mongosh --authenticationDatabase admin -u bionexus_admin -p bionexus_dev_password --eval "db.adminCommand('ping')" > /dev/null 2>&1 && echo "  ✓ MongoDB OK" || echo "  ✗ MongoDB FAILED"
	@echo ""
	@echo "Testing DuckDB..."
	@test -f data_lake/bionexus.duckdb && echo "  ✓ DuckDB OK" || echo "  ✗ DuckDB NOT INITIALIZED"

# Shell Access
postgres-shell:
	$(COMPOSE) exec postgres psql -U bionexus_user -d bionexus

neo4j-shell:
	$(COMPOSE) exec neo4j bin/cypher-shell -u neo4j -p bionexus_dev_password

mongo-shell:
	$(COMPOSE) exec mongodb mongosh -u bionexus_admin -p bionexus_dev_password --authenticationDatabase admin

duckdb-shell: lake-init
	python3 -c "import duckdb; conn = duckdb.connect('data_lake/bionexus.duckdb'); print('🦆 DuckDB Shell'); print('Type .help or .exit'); import code; code.interact(local={'conn': conn, 'execute': conn.execute})"

# Cleanup
clean:
	@echo "⚠️  WARNING: This will remove all volumes and data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(COMPOSE) down -v; \
		rm -rf data_lake/bionexus.duckdb; \
		echo "✓ Cleaned up"; \
	else \
		echo "Cancelled"; \
	fi

# Utility
status:
	@$(COMPOSE) ps

pull:
	$(COMPOSE) pull

build:
	$(COMPOSE) build

.DEFAULT_GOAL := help
