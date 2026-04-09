.PHONY: %

PROJECT_NAME=vertical-slices-template
DB_SERVICE_NAME=postgres
MAIN_SERVICE_NAME=api
DOCKER_COMPOSE_ENV_FILE=.env.dev
SRC_DIR=backend

# Requirements #

requirements:
	uv export --no-dev --format requirements-txt > $(SRC_DIR)/requirements.txt

requirements-dev:
	uv export --format requirements-txt > $(SRC_DIR)/requirements-dev.txt

requirements-all:
	$(MAKE) requirements; $(MAKE) requirements-dev

# Formatting and linting #

format:
	uv run ruff format $(SRC_DIR)

lint:
	uv run ruff check $(SRC_DIR)

lint-fix:
	uv run ruff check $(SRC_DIR) --fix

check-types:
	uv run mypy $(SRC_DIR)/app

code-cleanup:
	$(MAKE) format; $(MAKE) lint-fix; $(MAKE) check-types

code-analysis-cc:
	uv run radon cc $(SRC_DIR) -a -s

code-analysis-metrics:
	uv run radon raw $(SRC_DIR) -s

precommit-install:
	uv run pre-commit install

# Backend #

DOCKER_COMPOSE_COMMAND_DEV=\
	docker compose \
	--env-file $(DOCKER_COMPOSE_ENV_FILE) \
	--project-name $(PROJECT_NAME) \
	--file docker-compose.yaml

up:
	$(DOCKER_COMPOSE_COMMAND_DEV) up $(MAIN_SERVICE_NAME) --build $(ARGS)

# Run mock data script
mock-data:
	$(DOCKER_COMPOSE_COMMAND_DEV) exec -T $(DB_SERVICE_NAME) \
	psql -U postgres -d postgres -f - < backend/scripts/mock-data.sql

down:
	$(DOCKER_COMPOSE_COMMAND_DEV) down

down-clean:
	$(DOCKER_COMPOSE_COMMAND_DEV) down -v

# Alembic (database migrations) #

alembic-new:
	$(DOCKER_COMPOSE_COMMAND_DEV) exec $(MAIN_SERVICE_NAME) \
	alembic revision --autogenerate -m "$(MSG)"

alembic-upgrade:
	$(DOCKER_COMPOSE_COMMAND_DEV) exec $(MAIN_SERVICE_NAME) alembic upgrade head

# Postgres #

postgres-up:
	$(DOCKER_COMPOSE_COMMAND_DEV) up $(DB_SERVICE_NAME) -d

postgres-down:
	$(DOCKER_COMPOSE_COMMAND_DEV) down $(DB_SERVICE_NAME)

access-postgres:
	$(DOCKER_COMPOSE_COMMAND_DEV) exec $(DB_SERVICE_NAME) \
	psql -U postgres $(ARGS)

# Run SQL file and get CSV output
# Usage: make run-sql SQL_FILE=path/to/query.sql
run-sql:
	$(DOCKER_COMPOSE_COMMAND_DEV) cp $(SQL_FILE) \
	$(DB_SERVICE_NAME):/tmp/query.sql

	$(DOCKER_COMPOSE_COMMAND_DEV) exec $(DB_SERVICE_NAME) \
	bash -c "psql -U postgres --csv -f /tmp/query.sql > /tmp/output.csv"

	$(DOCKER_COMPOSE_COMMAND_DEV) cp $(DB_SERVICE_NAME):/tmp/output.csv \
	./output.csv

# Deletes Postgres data by deleting the Docker volumes
# Launches a Postgres container with the dir with the backup file mounted
# Waits for Postgres to be ready, and executes pg_restore
# Stops the Postgres container; and relaunches a new container
# without the backup directory mounted in the background
load-db-dump:
	$(DOCKER_COMPOSE_COMMAND_DEV) down --volumes

	$(DOCKER_COMPOSE_COMMAND_DEV) run --rm --name pg-backup -d -v \
	$(DB_DUMP_PATH):/db-dump postgres

	while true; do \
		$(DOCKER_COMPOSE_COMMAND_DEV) exec $(DB_SERVICE_NAME) \
		pg_isready -U postgres && break; \
	done

	@sleep 2

	$(DOCKER_COMPOSE_COMMAND_DEV) exec -T $(DB_SERVICE_NAME) \
	psql -U postgres -d postgres -f /db-dump || true

	docker stop pg-backup

	$(DOCKER_COMPOSE_COMMAND_DEV) up -d $(DB_SERVICE_NAME)

# Tests #

DOCKER_COMPOSE_COMMAND_TEST=\
	docker compose \
	--env-file $(DOCKER_COMPOSE_ENV_FILE) \
	--project-name $(PROJECT_NAME)-test \
	--file docker-compose.yaml \
	--file docker-compose.test.yaml

test:
	$(DOCKER_COMPOSE_COMMAND_TEST) run --rm --build --remove-orphans \
	$(MAIN_SERVICE_NAME) bash -c "alembic upgrade head && \
	python3 /src/scripts/initial_data.py && \
	pytest /src/tests --cov=app --cov-report=term-missing --cov-report=html \
	$(ARGS)"

test-down:
	$(DOCKER_COMPOSE_COMMAND_TEST) down -v

test-clean:
	$(MAKE) test; $(MAKE) test-down

test-access-postgres:
	$(DOCKER_COMPOSE_COMMAND_TEST) exec $(DB_SERVICE_NAME) \
	psql -U postgres $(ARGS)

# Helper #

help:
	@echo "Available commands:"
	@echo "  make requirements                 - Export production dependencies to requirements.txt"
	@echo "  make requirements-dev             - Export development dependencies to requirements-dev.txt"
	@echo "  make requirements-all             - Export both production and development dependencies"
	@echo "  make format                       - Format code with ruff"
	@echo "  make lint                         - Check code with ruff"
	@echo "  make lint-fix                     - Fix linting issues with ruff"
	@echo "  make check-types                  - Check types with mypy"
	@echo "  make code-cleanup                 - Run format, lint-fix and check-types at once"
	@echo "  make code-analysis-cc             - Run cyclomatic complexity analysis with radon"
	@echo "  make code-analysis-metrics        - Run code metrics analysis with radon"
	@echo "  make precommit-install            - Install pre-commit hooks"
	@echo "  make up                           - Start containers"
	@echo "  make mock-data                    - Run mock data script"
	@echo "  make down                         - Stop containers"
	@echo "  make down-clean                   - Stop containers and delete assets"
	@echo "  make alembic-new MSG=..           - Create new Alembic migration (autogenerate)"
	@echo "  make alembic-upgrade              - Upgrade Alembic to head"
	@echo "  make postgres-up                  - Start only Postgres container"
	@echo "  make postgres-down                - Stop only Postgres container"
	@echo "  make access-postgres              - Access Postgres container with psql"
	@echo "  make run-sql SQL_FILE=..          - Run SQL file and get CSV output"
	@echo "  make load-db-dump DB_DUMP_PATH=.. - Load database backup from SQL file"
	@echo "  make test                         - Run tests in separate container and database"
	@echo "  make test-down                    - Stop and remove test containers"
	@echo "  make test-clean                   - Run tests and delete assets"
	@echo "  make test-access-postgres         - Access test Postgres container with psql"
	@echo "  make help                         - Show this help message"
