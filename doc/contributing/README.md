# 🤝 Contributing to MapsProveFiber

Thank you for your interest in contributing! This guide will help you get started.

---

## 📚 Contributing Documents

| Document | Description | Audience |
|----------|-------------|----------|
| **[CODE_STYLE.md](CODE_STYLE.md)** | Code standards and conventions | All developers |
| **[PR_GUIDELINES.md](PR_GUIDELINES.md)** | Pull request guidelines | All contributors |
| **[TESTING_STANDARDS.md](TESTING_STANDARDS.md)** | Test quality standards | Test authors |

---

## 🚀 Quick Start for Contributors

### 1. Fork & Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/provemaps_beta.git
cd provemaps_beta
```

---

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Run tests to ensure everything works
pytest -q
```

See [../getting-started/QUICKSTART.md](../getting-started/QUICKSTART.md) for detailed setup (unified local + Docker). Deprecated: QUICKSTART_LOCAL.md.

---

### 3. Create a Branch

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Or bug fix branch
git checkout -b fix/bug-description
```

**Branch naming**:
- `feature/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation changes
- `refactor/` — Code refactoring
- `test/` — Test improvements

---

### 4. Make Changes

Follow our coding standards:

- **Format code**: `make fmt` (runs ruff + black + isort)
- **Lint code**: `make lint`
- **Run tests**: `pytest -q`
- **Check coverage**: `pytest --cov=. --cov-report=html`

See [CODE_STYLE.md](CODE_STYLE.md) for detailed standards.

---

### 5. Write Tests

All code changes require tests:

- **New features**: Add tests in `tests/` or app-specific `tests/`
- **Bug fixes**: Add regression test
- **Refactoring**: Ensure existing tests pass

See [TESTING_STANDARDS.md](TESTING_STANDARDS.md) for test guidelines.

---

### 6. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new feature X"
```

**Commit message format**:
```
<type>: <subject>

[optional body]

[optional footer]
```

**Types**:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `style:` — Code formatting (no logic change)
- `refactor:` — Code refactoring
- `test:` — Test changes
- `chore:` — Build/tooling changes

---

### 7. Push & Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# Use the PR template
```

See [PR_GUIDELINES.md](PR_GUIDELINES.md) for PR best practices.

---

## 🎯 Contribution Guidelines

### What We Look For

✅ **Good Contributions**:
- Clear problem statement
- Follows coding standards
- Includes tests
- Updates documentation
- Small, focused changes

❌ **Avoid**:
- Large, unfocused PRs
- Missing tests
- Breaking changes without discussion
- Undocumented code
- Style-only changes without value

---

### Code Review Process

1. **Automated Checks**
   - Tests must pass
   - Linting must pass
   - Coverage must not decrease

2. **Manual Review**
   - Code quality
   - Architecture fit
   - Test quality
   - Documentation

3. **Approval**
   - At least 1 maintainer approval
   - All comments addressed
   - CI green

4. **Merge**
   - Squash and merge (default)
   - Rebase if linear history needed

---

## 📋 Types of Contributions

### Bug Fixes

1. **Open an issue** (if not already exists)
2. **Create branch**: `fix/issue-123-description`
3. **Add regression test**
4. **Fix the bug**
5. **Submit PR** referencing issue

---

### New Features

1. **Discuss in issue first** (for large features)
2. **Create branch**: `feature/feature-name`
3. **Implement with tests**
4. **Update documentation**
5. **Submit PR**

---

### Documentation

1. **Create branch**: `docs/topic`
2. **Update/add documentation**
3. **Check links and formatting**
4. **Submit PR**

Documentation contributions are always welcome!

---

### Tests

1. **Identify coverage gaps**
2. **Create branch**: `test/coverage-area`
3. **Write tests**
4. **Verify coverage increase**
5. **Submit PR**

---

## 🛠️ Development Workflow

### Daily Development

```bash
# Pull latest changes
git pull origin main

# Create branch
git checkout -b feature/my-feature

# Make changes, run tests frequently
pytest -q

# Format code before committing
make fmt

# Commit
git commit -m "feat: implement feature X"

# Push
git push origin feature/my-feature
```

---

### Testing Workflow

```bash
# Run all tests
pytest -q

# Run specific test file
pytest tests/test_inventory.py -v

# Run specific test
pytest tests/test_inventory.py::test_site_creation -v

# Run with coverage
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html  # On macOS
# On Windows: start htmlcov\index.html
```

See [TESTING_STANDARDS.md](TESTING_STANDARDS.md) for more.

---

## 📖 Code Standards

### Python Code Style

- **Formatter**: Black (line length 100)
- **Linter**: Ruff
- **Import sorting**: isort
- **Type hints**: Encouraged (not required)

```bash
# Auto-format
make fmt

# Check style
make lint
```

See [CODE_STYLE.md](CODE_STYLE.md) for details.

---

### Django Best Practices

- Use Django ORM (avoid raw SQL)
- Keep views thin (business logic in services)
- Use Django forms for validation
- Follow Django naming conventions
- Write migrations for schema changes

---

### Documentation Standards

- **Markdown**: Use proper formatting
- **Code blocks**: Specify language
- **Links**: Use relative paths
- **Structure**: Clear headings and sections

---

## 🔍 Finding Issues to Work On

### Good First Issues

Look for issues labeled:
- `good first issue` — Easy for newcomers
- `help wanted` — Maintainers need help
- `bug` — Bug fixes
- `documentation` — Docs improvements

### Before Starting

1. **Check if issue is assigned**
2. **Comment that you're working on it**
3. **Ask questions if unclear**
4. **Discuss approach for large changes**

---

## 🆘 Getting Help

### Questions?

- **Development questions**: Open a discussion
- **Bug reports**: Open an issue
- **Feature requests**: Open an issue with proposal
- **Security issues**: Email maintainers directly

### Resources

- [Getting Started Guide](../getting-started/QUICKSTART.md)
- [Architecture Documentation](../architecture/OVERVIEW.md)
- [API Reference](../api/ENDPOINTS.md)
- [Development Guide](../guides/DEVELOPMENT.md)

---

## 🎓 Learning Path for Contributors

**Week 1**: Setup and basics
1. Complete [quickstart](../getting-started/QUICKSTART.md)
2. Read [architecture overview](../architecture/OVERVIEW.md)
3. Run tests, explore codebase
4. Fix a typo in documentation (practice PR workflow)

**Week 2**: First contribution
1. Find a `good first issue`
2. Discuss approach with maintainers
3. Implement with tests
4. Submit PR

**Week 3+**: Regular contributions
1. Tackle more complex issues
2. Propose new features
3. Help review other PRs
4. Improve documentation

---

## ✅ Pull Request Checklist

Before submitting your PR:

- [ ] Tests added/updated and passing
- [ ] Code formatted (`make fmt`)
- [ ] Linting passing (`make lint`)
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow convention
- [ ] PR description is clear
- [ ] Issue linked (if applicable)
- [ ] Branch is up to date with main

See [PR_GUIDELINES.md](PR_GUIDELINES.md) for complete checklist.

---

## 🏆 Recognition

Contributors are recognized in:
- Release notes
- CONTRIBUTORS.md file
- GitHub contributors page

Thank you for making MapsProveFiber better! 🎉

---

## 📖 Related Documentation

- **[Code Style Guide](CODE_STYLE.md)** — Coding standards
- **[PR Guidelines](PR_GUIDELINES.md)** — Pull request best practices
- **[Testing Standards](TESTING_STANDARDS.md)** — Test quality guidelines
- **[Development Guide](../guides/DEVELOPMENT.md)** — Daily workflows

---

**Ready to contribute?** Pick an issue and get started! 🚀
