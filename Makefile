.PHONY: help install fmt lint test test-live cov index qa ask up down agents clean

PY := .venv/bin/python
PIP := .venv/bin/pip

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Create the venv and install the project with dev extras
	python3 -m venv .venv
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -e ".[dev]"
	@echo "installed. copy deploy/.env.example to .env to override any setting."

fmt:  ## Format with ruff
	$(PY) -m ruff format psiog_kendra agents tests

lint:  ## Lint with ruff
	$(PY) -m ruff check psiog_kendra agents tests

test:  ## Run the offline test suite (no LLM, no network)
	$(PY) -m pytest

test-live:  ## Run the tests that call the real local models (needs ~4 GiB free RAM)
	$(PY) -m pytest --live

cov:  ## Test suite with a coverage report (target: >=80%)
	$(PY) -m pytest --cov=psiog_kendra --cov-report=term-missing --cov-fail-under=80

index:  ## Chunk + embed the docs corpus into the vector index (run once)
	$(PY) -m psiog_kendra.index_docs

qa:  ## Run the 12 test queries + Judge Agent, emit the QA evidence report
	$(PY) -m psiog_kendra.qa.report

qa-resume:  ## Continue a killed QA run: keep what is in the report, run only what is missing
	$(PY) -m psiog_kendra.qa.report --resume

qa-only:  ## Re-run just one or more queries, e.g. make qa-only Q=4  /  make qa-only Q=4,7
	$(PY) -m psiog_kendra.qa.report --only "$(Q)"

qa-rejudge:  ## Re-grade the stored answers without asking them again (12 LLM calls, not 60).
	## Use ONLY when a fix changed how answers are scored, not how they are produced.
	$(PY) -m psiog_kendra.qa.report --rejudge

evidence:  ## Regenerate docs/qa/ (one evidence page per test query) from the QA report
	$(PY) -m psiog_kendra.qa.evidence

ask:  ## Ask the copilot one question:  make ask Q="did the sales etl run?"
	@$(PY) -m psiog_kendra.cli "$(Q)"

up:  ## Start the AgentField control plane
	docker compose -f deploy/docker-compose.yml up -d
	@echo "control plane: $${AGENTFIELD_SERVER:-http://localhost:8080}"

down:  ## Stop the control plane
	docker compose -f deploy/docker-compose.yml down

agents:  ## Register all 5 agents with the running control plane
	$(PY) -m agents.data_agent &
	$(PY) -m agents.devops_agent &
	$(PY) -m agents.crm_agent &
	$(PY) -m agents.docs_agent &
	$(PY) -m agents.coordinator &
	@echo "5 agents registering with the control plane"

clean:
	rm -rf .pytest_cache .coverage .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
