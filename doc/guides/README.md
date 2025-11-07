# 📘 Developer & Operations Guides

Comprehensive guides for daily development, testing, and operations.

---

## 📚 Available Guides

### For Developers

| Guide | Description | Key Topics |
|-------|-------------|------------|
| **[DEVELOPMENT.md](DEVELOPMENT.md)** | Daily development workflow | Local setup, commands, debugging, hot reload |
| **[TESTING.md](TESTING.md)** | Testing best practices | pytest, coverage, fixtures, CI/CD |
| **[DOCKER.md](DOCKER.md)** | Docker development | Compose, volumes, networking, debugging |

### For Operations

| Guide | Description | Key Topics |
|-------|-------------|------------|
| **[OBSERVABILITY.md](OBSERVABILITY.md)** | Monitoring and metrics | Prometheus, health checks, logging, alerts |

---

## 🚀 Quick Links

### Development
- [Run development server](DEVELOPMENT.md#running-the-server)
- [Run tests](TESTING.md#running-tests)
- [Format code](DEVELOPMENT.md#code-formatting)
- [Debug with Docker](DOCKER.md#debugging)

### Testing
- [Test structure](TESTING.md#test-structure)
- [Writing tests](TESTING.md#writing-tests)
- [Coverage reports](TESTING.md#coverage)
- [CI/CD integration](TESTING.md#cicd)

### Observability
- [Health check endpoints](OBSERVABILITY.md#health-checks)
- [Prometheus metrics](OBSERVABILITY.md#metrics)
- [Logging best practices](OBSERVABILITY.md#logging)
- [Grafana dashboards](OBSERVABILITY.md#grafana)

---

## 🎯 Common Workflows

### Daily Development Workflow

```bash
# 1. Pull latest changes
git pull origin main

# 2. Update dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Start development server
make run

# 5. Run tests before committing
pytest -q

# 6. Format code
make fmt
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed workflow.

---

### Test-Driven Development (TDD)

```bash
# 1. Write failing test
# Edit tests/test_feature.py

# 2. Run specific test
pytest tests/test_feature.py::test_new_feature -v

# 3. Implement feature
# Edit source code

# 4. Run tests until passing
pytest tests/test_feature.py -v

# 5. Run full test suite
pytest -q

# 6. Check coverage
pytest --cov=. --cov-report=html
```

See [TESTING.md](TESTING.md) for TDD best practices.

---

### Docker Development Workflow

```bash
# 1. Start services
docker-compose up -d

# 2. View logs
docker-compose logs -f web

# 3. Run migrations in container
docker-compose exec web python manage.py migrate

# 4. Run tests in container
docker-compose exec web pytest -q

# 5. Restart after code changes
docker-compose restart web

# 6. Stop services
docker-compose down
```

See [DOCKER.md](DOCKER.md) for Docker workflows.

---

## 📊 Monitoring Workflow

### Local Development

```bash
# Check health
curl http://localhost:8000/healthz/

# View metrics
curl http://localhost:8000/metrics/

# Check readiness
curl http://localhost:8000/ready/

# Check liveness
curl http://localhost:8000/live/
```

### Production

- **Prometheus**: `http://prometheus:9090/targets`
- **Grafana**: `http://grafana:3000/dashboards`
- **Alerts**: Check AlertManager

See [OBSERVABILITY.md](OBSERVABILITY.md) for monitoring setup.

---

## 🔧 Troubleshooting

### Development Issues

| Problem | Solution | Guide |
|---------|----------|-------|
| Server won't start | Check ports, migrations | [DEVELOPMENT.md](DEVELOPMENT.md#troubleshooting) |
| Tests failing | Check fixtures, database | [TESTING.md](TESTING.md#troubleshooting) |
| Docker build fails | Check Dockerfile, cache | [DOCKER.md](DOCKER.md#troubleshooting) |
| Metrics not appearing | Check Prometheus config | [OBSERVABILITY.md](OBSERVABILITY.md#troubleshooting) |

See also: [../operations/TROUBLESHOOTING.md](../operations/TROUBLESHOOTING.md)

---

## 🎓 Learning Path

**New to the project?** Follow this learning path:

1. **Week 1**: Setup and basics
   - Complete [../getting-started/QUICKSTART.md](../getting-started/QUICKSTART.md)
   - Read [DEVELOPMENT.md](DEVELOPMENT.md)
   - Run your first test with [TESTING.md](TESTING.md)

2. **Week 2**: Development workflow
   - Understand architecture: [../architecture/OVERVIEW.md](../architecture/OVERVIEW.md)
   - Practice TDD workflow
   - Set up Docker: [DOCKER.md](DOCKER.md)

3. **Week 3**: Advanced topics
   - Explore API: [../api/ENDPOINTS.md](../api/ENDPOINTS.md)
   - Set up monitoring: [OBSERVABILITY.md](OBSERVABILITY.md)
   - Contribute: [../contributing/README.md](../contributing/README.md)

---

## 📖 Related Documentation

- **[Getting Started](../getting-started/)** — Installation and setup
- **[Architecture](../architecture/)** — System design
- **[API Reference](../api/)** — REST API documentation
- **[Operations](../operations/)** — Production deployment

---

**Questions?** Check [../README.md](../README.md) or open an issue.
