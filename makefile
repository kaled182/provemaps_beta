# Makefile — atalhos para desenvolvimento e manutenção do mapsprovefiber
# Dica: execute apenas `make` para ver a ajuda.

PY := python
MANAGE := $(PY) manage.py
DJANGO_SETTINGS_MODULE ?= settings.dev
export DJANGO_SETTINGS_MODULE

# Endpoints locais de saúde (ajuste se necessário)
HEALTH_URL ?= http://localhost:8000/healthz
READY_URL  ?= http://localhost:8000/ready
LIVE_URL   ?= http://localhost:8000/live

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Mostra esta ajuda
	@echo "Uso: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_.-]+:.*?## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

### ---------------------------
### Django (desenvolvimento)
### ---------------------------

.PHONY: run
run:  ## Roda o servidor Django em 0.0.0.0:8000
	$(MANAGE) runserver 0.0.0.0:8000

.PHONY: migrate
migrate:  ## Aplica migrações
	$(MANAGE) migrate

.PHONY: makemigrations
makemigrations:  ## Gera migrações
	$(MANAGE) makemigrations

.PHONY: superuser
superuser:  ## Cria superusuário (interativo)
	$(MANAGE) createsuperuser

.PHONY: collectstatic
collectstatic:  ## Coleta arquivos estáticos
	$(MANAGE) collectstatic --noinput

.PHONY: shell
shell:  ## Abre Django shell
	$(MANAGE) shell

### ---------------------------
### Dependências & limpeza
### ---------------------------

.PHONY: requirements
requirements:  ## Instala dependências do projeto
	pip install -r requirements.txt

.PHONY: clean
clean:  ## Remove caches e artefatos temporários
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	rm -rf .pytest_cache .coverage htmlcov

# Requer django-extensions para reset_db (opcional)
.PHONY: resetdb
resetdb:  ## Reseta o banco (CUIDADO: apaga dados!)
	-$(MANAGE) reset_db --noinput
	$(MANAGE) migrate
	-$(MANAGE) createsuperuser --noinput --username admin --email admin@localhost

### ---------------------------
### Testes e qualidade
### ---------------------------

.PHONY: test
test:  ## Roda testes rapidamente (pytest -q)
	pytest -q

.PHONY: test-verbose
test-verbose:  ## Roda testes com output detalhado
	pytest -v

.PHONY: test-coverage
test-coverage:  ## Roda testes com cobertura + HTML
	pytest --cov --cov-report=html

.PHONY: test-specific
test-specific:  ## Roda testes específicos. Uso: make test-specific path=core/tests/test_views.py
	pytest -v $(path)

.PHONY: lint
lint:  ## Checa formatação/estilo (ruff/black/isort)
	ruff check .
	black --check .
	isort --check-only .

.PHONY: fmt
fmt:  ## Formata código (ruff --fix / black / isort)
	ruff check . --fix
	black .
	isort .

### ---------------------------
### Docker Compose
### ---------------------------

.PHONY: up
up:  ## Sobe stack via docker compose (arquivo padrão ./docker-compose.yml)
	docker compose up -d

.PHONY: down
down:  ## Derruba stack docker compose
	docker compose down

.PHONY: logs
logs:  ## Mostra logs dos containers (follow)
	docker compose logs -f

.PHONY: build
build:  ## Constrói as imagens
	docker compose build

.PHONY: restart
restart:  ## Reinicia os serviços
	docker compose restart

### ---------------------------
### Health checks (local)
### ---------------------------

.PHONY: health
health:  ## Verifica saúde da aplicação (/healthz)
	curl -fsS "$(HEALTH_URL)" >/dev/null

.PHONY: ready
ready:  ## Verifica readiness (/ready)
	curl -fsS "$(READY_URL)" >/dev/null

.PHONY: live
live:  ## Verifica liveness (/live)
	curl -fsS "$(LIVE_URL)" >/dev/null

### ---------------------------
### Produção (helpers)
### ---------------------------

.PHONY: prod-migrate
prod-migrate:  ## Aplica migrações com settings de produção
	DJANGO_SETTINGS_MODULE=settings.prod $(MANAGE) migrate

.PHONY: prod-collectstatic
prod-collectstatic:  ## Collectstatic com settings de produção
	DJANGO_SETTINGS_MODULE=settings.prod $(MANAGE) collectstatic --noinput

.PHONY: deploy
deploy:  ## Executa o deploy (scripts/deploy.sh)
	./scripts/deploy.sh
