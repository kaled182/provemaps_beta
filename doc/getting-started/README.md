# 🚀 Getting Started

Welcome! This section helps you get MapsProveFiber running quickly.

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** (check: `python --version`)
- **Node.js 18+** (for frontend assets)
- **Docker** (optional, for containerized setup)
- **Git** (to clone the repository)

## 🎯 Quick Start Paths

Choose the best path for your needs:

### Path 1: Local Development (Recommended)
**Best for**: Active development, debugging, learning codebase

→ See [QUICKSTART.md](QUICKSTART.md)

**Steps**:
1. Clone repository
2. Install Python dependencies
3. Configure local settings
4. Run migrations
5. Start development server

**Time**: ~15 minutes

---

### Path 2: Docker Compose (Easy)
**Best for**: Quick demo, isolated environment, production-like setup

→ See [QUICKSTART.md](QUICKSTART.md#-setup-docker-stack-completa)

**Steps**:
1. Clone repository
2. Create `.env` file
3. Run `docker-compose up`

**Time**: ~5 minutes

---

## 📖 Available Guides

| Guide | Description | Audience |
|-------|-------------|----------|
| [QUICKSTART.md](QUICKSTART.md) | Unified local + Docker quickstart | Developers, DevOps |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common setup issues | Everyone |

---

## ⚡ Quick Commands

After installation, use these commands:

```bash
# Start development server
make run

# Run tests
pytest -q

# Format code
make fmt

# Check health
make health
```

See [../guides/DEVELOPMENT.md](../guides/DEVELOPMENT.md) for complete command reference.

---

## 🎓 Next Steps

After completing the quickstart:

1. **Explore the Dashboard**
   - Navigate to `http://localhost:8000/maps/`
   - Check real-time status
   - Explore inventory data

2. **Read Core Guides**
   - [Development Guide](../guides/DEVELOPMENT.md) — Daily workflows
   - [Testing Guide](../guides/TESTING.md) — Run and write tests
   - [API Guide](../api/ENDPOINTS.md) — Use the REST API

3. **Understand Architecture**
   - [Architecture Overview](../architecture/OVERVIEW.md) — System design
   - [Module Reference](../architecture/MODULES.md) — App structure

---

## 🆘 Getting Help

**Stuck during setup?**
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review [../operations/TROUBLESHOOTING.md](../operations/TROUBLESHOOTING.md)
3. Open a GitHub issue with error details

---

**Ready to start?** Pick a quickstart path above! 🚀
