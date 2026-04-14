PYTHON ?= python3
PACKAGE = research_pulse_cn

.PHONY: install run run-api migrate seed worker run-worker run-scheduler scheduler-tick lint format test check docker-up docker-down

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

run:
	$(MAKE) run-api

run-api:
	uvicorn $(PACKAGE).main:app --factory --reload --host 127.0.0.1 --port 8000

migrate:
	alembic upgrade head

seed:
	$(PYTHON) -m $(PACKAGE).seed

worker:
	$(PYTHON) -m $(PACKAGE).worker.main --once

run-worker:
	$(PYTHON) -m $(PACKAGE).worker.main --limit 20 --poll-interval 15

run-scheduler:
	$(PYTHON) -m $(PACKAGE).scheduler.main --poll-interval 60

scheduler-tick:
	$(PYTHON) -m $(PACKAGE).scheduler.main --once

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
