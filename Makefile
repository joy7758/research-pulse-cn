PYTHON ?= python3
PACKAGE = research_pulse_cn

.PHONY: install run migrate seed worker lint format test check docker-up docker-down

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

run:
	uvicorn $(PACKAGE).main:app --factory --reload --host 127.0.0.1 --port 8000

migrate:
	alembic upgrade head

seed:
	$(PYTHON) -m $(PACKAGE).seed

worker:
	$(PYTHON) -m $(PACKAGE).worker.main --once

lint:
	ruff check .

format:
	ruff format .

test:
	pytest

check: lint test

docker-up:
	docker compose up -d postgres redis

docker-down:
	docker compose down
