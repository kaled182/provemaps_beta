# 📦 Release Documentation

Version history, changelogs, and migration guides.

---

## 📚 Release Documents

| Document | Description |
|----------|-------------|
| **[v2.0.1/CHANGELOG.md](v2.0.1/CHANGELOG.md)** | Version 2.0.1 changelog |
| **[v2.0.0/CHANGELOG.md](v2.0.0/CHANGELOG.md)** | Version 2.0.0 changelog |
| **[v2.0.0/BREAKING_CHANGES.md](v2.0.0/BREAKING_CHANGES.md)** | Breaking changes and migration guide |
| **[v2.0.0/](v2.0.0/)** | Version 2.0.0 specific documentation |

---

## 🎯 Current Version

**Version**: 2.0.1 (Fiber Route Builder stabilization)  
**Release Date**: 2025-11-11  
**Status**: Stable

### What's New in v2.0.1

✅ **Fiber Route Builder restored**
- Updated template keeps advanced workflow panels without duplicated Django blocks
- Corrected ES module asset path so Google Maps callback initializes successfully
- UI copy audited for English-only strings to align with project standard

See [v2.0.1/CHANGELOG.md](v2.0.1/CHANGELOG.md) for full notes.

### What's New in v2.0.0

✅ **Modular Architecture**
- Separated concerns into distinct Django apps
- `inventory` as single source of truth
- `integrations/zabbix/` resilient client
- `monitoring` for combined health checks

✅ **API-First Design**
- REST API at `/api/v1/inventory/*`
- Removed legacy `/zabbix_api/*` endpoints
- Versioned endpoints

✅ **Resilience & Observability**
- Circuit breaker for Zabbix integration
- Comprehensive Prometheus metrics
- Health checks at multiple levels
- Graceful degradation

See [v2.0.0/](v2.0.0/) for complete release notes.

---

## 🚨 Breaking Changes (v2.0.0)

⚠️ **Important**: Version 2.0.0 introduces breaking changes.

### Module Removals

- ❌ **`zabbix_api/` module removed**
  - **Migration**: Use `inventory`, `monitoring`, `integrations/zabbix`
  - **Impact**: All imports must be updated

### API Changes

- ❌ **`/zabbix_api/*` endpoints removed**
  - **Migration**: Use `/api/v1/inventory/*`
  - **Impact**: All API clients must be updated

### Import Changes

```python
# ❌ OLD (v1.x)
from zabbix_api.models import Site
from zabbix_api.services import get_sites

# ✅ NEW (v2.0.0)
from inventory.models import Site
from inventory.services import site_service
```

See [v2.0.0/BREAKING_CHANGES.md](v2.0.0/BREAKING_CHANGES.md) for complete migration guide.

---

## 📖 Version History

### v2.0.0 (2025-01-07) - Modular Architecture

**Major Changes**:
- Modular Django architecture
- Removed `zabbix_api/` module
- API-first design
- Resilient integrations
- Complete observability stack

**Migration Required**: Yes  
**Upgrade Time**: ~2 hours  
**Rollback**: Supported (database compatible)

See [v2.0.0/CHANGELOG.md](v2.0.0/CHANGELOG.md) for detailed changes.

---

### v1.x (Legacy)

**Status**: Deprecated  
**Support**: Security fixes only until 2025-03-31  
**Migration**: Recommended to upgrade to v2.0.0

---

## 🔄 Migration Guides

### Upgrading from v1.x to v2.0.0

**Estimated Time**: 2 hours  
**Difficulty**: Medium  
**Rollback**: Supported

**Steps**:

1. **Pre-Migration**
   - [ ] Backup database
   - [ ] Review breaking changes
   - [ ] Update dependencies
   - [ ] Run tests on v1.x

2. **Code Migration**
   - [ ] Update imports (see [BREAKING_CHANGES.md](v2.0.0/BREAKING_CHANGES.md))
   - [ ] Update API calls
   - [ ] Update tests
   - [ ] Update configurations

3. **Database Migration**
   - [ ] Run migrations
   - [ ] Verify data integrity
   - [ ] Test critical paths

4. **Validation**
   - [ ] All tests passing
   - [ ] API endpoints working
   - [ ] Zabbix integration functional
   - [ ] Monitoring operational

See [v2.0.0/BREAKING_CHANGES.md](v2.0.0/BREAKING_CHANGES.md) for complete guide.

---

## 📋 Release Checklist

Before releasing a new version:

### Development
- [ ] All features implemented
- [ ] All tests passing
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] Changelog updated

### Pre-Release
- [ ] Version bumped
- [ ] Migration guide created (if breaking changes)
- [ ] Release notes drafted
- [ ] Security audit completed
- [ ] Performance tested

### Release
- [ ] Tag created
- [ ] Docker image built
- [ ] Release published
- [ ] Announcement sent
- [ ] Monitoring active

### Post-Release
- [ ] Monitor errors
- [ ] Check health metrics
- [ ] Respond to issues
- [ ] Update documentation

---

## 🎯 Support Policy

### Version Support

| Version | Status | Support Until | Notes |
|---------|--------|---------------|-------|
| **2.0.x** | Active | TBD | Current stable |
| **1.x** | Deprecated | 2025-03-31 | Security fixes only |

### Update Recommendations

- **Critical Security**: Update immediately
- **Breaking Changes**: Plan migration (2-4 weeks)
- **Features**: Update quarterly
- **Bug Fixes**: Update monthly

---

## 📖 Versioning Scheme

We follow [Semantic Versioning](https://semver.org/):

**Format**: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (API incompatibility)
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

**Examples**:
- `2.0.0` → `2.1.0`: New feature, no breaking changes
- `2.1.0` → `2.1.1`: Bug fix
- `2.1.1` → `3.0.0`: Breaking change

---

## 🔍 Finding Release Information

### By Version

- **v2.0.0**: [v2.0.0/](v2.0.0/)
- **v1.x**: [CHANGELOG.md](CHANGELOG.md#v1x) (legacy)

### By Topic

| Topic | Document |
|-------|----------|
| **All changes** | [CHANGELOG.md](CHANGELOG.md) |
| **Breaking changes** | [BREAKING_CHANGES.md](BREAKING_CHANGES.md) |
| **Migration from v1.x** | [v2.0.0/BREAKING_CHANGES.md](v2.0.0/BREAKING_CHANGES.md) |
| **Deployment** | [../operations/DEPLOYMENT.md](../operations/DEPLOYMENT.md) |

---

## 📦 Release Artifacts

### Docker Images

```bash
# Pull latest
docker pull mapsprove/fiber:latest

# Pull specific version
docker pull mapsprove/fiber:2.0.0

# Pull version tag
docker pull mapsprove/fiber:v2.0.0
```

### Source Code

```bash
# Clone repository
git clone https://github.com/kaled182/provemaps_beta.git

# Checkout specific version
git checkout v2.0.0
```

---

## 📖 Related Documentation

- **[Deployment Guide](../operations/DEPLOYMENT.md)** — Production deployment
- **[Architecture](../architecture/)** — System design
- **[API Reference](../api/)** — API documentation
- **[Contributing](../contributing/)** — Development guidelines

---

**Need help upgrading?** See [v2.0.0/BREAKING_CHANGES.md](v2.0.0/BREAKING_CHANGES.md) or open an issue.
