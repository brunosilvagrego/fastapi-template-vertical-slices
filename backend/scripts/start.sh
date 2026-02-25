#! /bin/bash

set -e

# Run migrations
alembic upgrade head

# Populate database with initial data
python3 /src/scripts/initial_data.py

# Run web server
UVICORN_FLAGS=""
[[ "$ENVIRONMENT" == "development" ]] && UVICORN_FLAGS="--reload"

uvicorn app.main:app --host 0.0.0.0 --port 80 $UVICORN_FLAGS
