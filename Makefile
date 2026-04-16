PYTHON ?= python3
NPM ?= npm
PACKAGE = research_pulse_cn
DESKTOP_DIR = apps/desktop
SUBSCRIPTION_EDITOR_WEB_DIR = apps/subscription-editor-web
export PATH := $(HOME)/.cargo/bin:$(PATH)

.PHONY: install run run-api migrate seed worker run-worker run-scheduler scheduler-tick bootstrap-admin lint format test check docker-up docker-down desktop-install desktop-dev desktop-lint desktop-test desktop-build-web subscription-editor-install subscription-editor-dev subscription-editor-lint subscription-editor-test subscription-editor-build

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

run:
	$(MAKE) run-api

run-api:
	$(PYTHON) -m uvicorn $(PACKAGE).main:app --factory --reload --host 127.0.0.1 --port 8000

migrate:
	$(PYTHON) -m alembic upgrade head

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

bootstrap-admin:
	@test -n "$(EMAIL)" || (echo "EMAIL is required" && exit 1)
	@test -n "$(PASSWORD)" || (echo "PASSWORD is required" && exit 1)
	$(PYTHON) -m $(PACKAGE).auth.bootstrap --email "$(EMAIL)" --password "$(PASSWORD)" $(if $(DISPLAY_NAME),--display-name "$(DISPLAY_NAME)",)

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

test:
	$(PYTHON) -m pytest

check: lint test

docker-up:
	docker compose up -d postgres redis

docker-down:
	docker compose down

desktop-install:
	cd $(DESKTOP_DIR) && $(NPM) install

desktop-dev:
	cd $(DESKTOP_DIR) && $(NPM) run tauri dev

desktop-lint:
	cd $(DESKTOP_DIR) && $(NPM) run lint && $(NPM) run typecheck

desktop-test:
	cd $(DESKTOP_DIR) && $(NPM) run test
	cd $(DESKTOP_DIR) && cargo test --manifest-path src-tauri/Cargo.toml

desktop-build-web:
	cd $(DESKTOP_DIR) && $(NPM) run build

subscription-editor-install:
	cd $(SUBSCRIPTION_EDITOR_WEB_DIR) && $(NPM) install

subscription-editor-dev:
	cd $(SUBSCRIPTION_EDITOR_WEB_DIR) && $(NPM) run dev

subscription-editor-lint:
	cd $(SUBSCRIPTION_EDITOR_WEB_DIR) && $(NPM) run lint
	cd $(SUBSCRIPTION_EDITOR_WEB_DIR) && $(NPM) run typecheck

subscription-editor-test:
	cd $(SUBSCRIPTION_EDITOR_WEB_DIR) && $(NPM) run test

subscription-editor-build:
	cd $(SUBSCRIPTION_EDITOR_WEB_DIR) && $(NPM) run build
