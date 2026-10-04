# Makefile - shortcuts for developing and maintaining mapsprovefiber
# Tip: run just `make` to see the help output.

PY := python
BACKEND_DIR := backend
MANAGE := $(PY) $(BACKEND_DIR)/manage.py
DJANGO_SETTINGS_MODULE ?= settings.dev
export DJANGO_SETTINGS_MODULE

COMPOSE := docker compose -f docker/docker-compose.yml

# Local health endpoints (adjust as needed)
HEALTH_URL ?= http://localhost:8000/healthz
READY_URL  ?= http://localhost:8000/ready
LIVE_URL   ?= http://localhost:8000/live

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Show this help menu
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_.-]+:.*?## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

### ---------------------------
### Django (development)
### ---------------------------

.PHONY: run
run:  ## Run Django development server on 0.0.0.0:8000
	$(MANAGE) runserver 0.0.0.0:8000

.PHONY: migrate
migrate:  ## Apply migrations
	$(MANAGE) migrate

.PHONY: makemigrations
makemigrations:  ## Generate migrations
	$(MANAGE) makemigrations

.PHONY: superuser
superuser:  ## Create superuser (interactive)
	$(MANAGE) createsuperuser

.PHONY: collectstatic
collectstatic:  ## Collect static files
	$(MANAGE) collectstatic --noinput

.PHONY: shell
shell:  ## Open Django shell
	$(MANAGE) shell

### ---------------------------
### Agent tooling (Claude Code)
### ---------------------------

.PHONY: skills
skills:  ## Repõe as skills de agente (.claude/skills/) a partir do skills-lock.json
	@./scripts/skills-install.sh

### ---------------------------
### Dependencies & cleanup
### ---------------------------

.PHONY: requirements
requirements:  ## Install backend runtime dependencies (what the production image gets)
	pip install -r $(BACKEND_DIR)/requirements.txt

.PHONY: requirements-dev
requirements-dev:  ## Install runtime + test/lint/type-check dependencies
	pip install -r $(BACKEND_DIR)/requirements-dev.txt

.PHONY: clean
clean:  ## Remove caches and temporary artifacts
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf .pytest_cache .coverage htmlcov

# Requires django-extensions for reset_db (optional)
.PHONY: resetdb
resetdb:  ## Reset database (WARNING: deletes data!)
	-$(MANAGE) reset_db --noinput
	$(MANAGE) migrate
	-$(MANAGE) createsuperuser --noinput --username admin --email admin@localhost

### ---------------------------
### Tests & quality
### ---------------------------

.PHONY: test
test:  ## Run tests quickly (pytest -q)
	pytest -q

.PHONY: test-verbose
test-verbose:  ## Run tests with verbose output
	pytest -v

.PHONY: test-coverage
test-coverage:  ## Run tests with coverage and HTML report
	pytest --cov --cov-report=html

.PHONY: test-specific
test-specific:  ## Run specific tests e.g. make test-specific path=core/tests/test_views.py
	pytest -v $(path)

.PHONY: lint
lint:  ## Check formatting/style (ruff/black/isort)
	ruff check .
	black --check .
	isort --check-only .

.PHONY: fmt
fmt:  ## Format code (ruff --fix / black / isort)
	ruff check . --fix
	black .
	isort .

.PHONY: lint-changed
lint-changed:  ## Lint only the Python files changed vs BASE (default origin/inicial) — what CI enforces (EV-0022)
	scripts/lint-changed.sh $(BASE)

.PHONY: precommit
precommit:  ## Install the pre-commit hooks (black/ruff/isort on staged files)
	pre-commit install

### ---------------------------
### Docker Compose
### ---------------------------

.PHONY: up
up:  ## Bring stack up via docker compose (docker/docker-compose.yml)
	$(COMPOSE) up -d

.PHONY: down
down:  ## Tear down docker compose stack
	$(COMPOSE) down

.PHONY: logs
logs:  ## Tail container logs
	$(COMPOSE) logs -f

.PHONY: build
build:  ## Build images
	$(COMPOSE) build

.PHONY: restart
restart:  ## Restart services
	$(COMPOSE) restart

### ---------------------------
### Health checks (local)
### ---------------------------

.PHONY: health
health:  ## Check application health (/healthz)
	curl -fsS "$(HEALTH_URL)" >/dev/null

.PHONY: ready
ready:  ## Check readiness (/ready)
	curl -fsS "$(READY_URL)" >/dev/null

.PHONY: live
live:  ## Check liveness (/live)
	curl -fsS "$(LIVE_URL)" >/dev/null

### ---------------------------
### Production helpers
### ---------------------------

.PHONY: prod-migrate
prod-migrate:  ## Apply migrations with production settings
	DJANGO_SETTINGS_MODULE=settings.prod $(MANAGE) migrate

.PHONY: prod-collectstatic
prod-collectstatic:  ## Run collectstatic with production settings
	DJANGO_SETTINGS_MODULE=settings.prod $(MANAGE) collectstatic --noinput

.PHONY: deploy
deploy:  ## Run deployment script (scripts/deploy.sh) — recusa árvore suja e coze GIT_SHA na imagem
	./scripts/deploy.sh

# ---- Central de Evolução (ADR 0006 / EV-0027) ----
EVOLUCAO_HEALTH_URL ?= $(HEALTH_URL)

.PHONY: evolucao-fechar
evolucao-fechar:  ## Fecha na Central os itens cujo commit `fecha EV-NNNN` já está no ar (lê git_sha do /healthz)
	EVOLUCAO_HEALTH_URL=$(EVOLUCAO_HEALTH_URL) ./scripts/evolucao_fechados.sh | $(MANAGE) evolucao_fechar

.PHONY: evolucao-quadro
evolucao-quadro:  ## Regenera o bloco EVOLUCAO do CLAUDE.md a partir da Central
	$(MANAGE) evolucao_quadro

.PHONY: evolucao-sync
evolucao-sync: evolucao-fechar evolucao-quadro  ## Fecha o que está no ar e regenera o quadro
