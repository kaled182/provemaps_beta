# Pull Request Guidelines - MapsProveFiber

**Version**: v2.0.0  
**Last Updated**: 2025-11-10

---

## 📖 Overview

This guide outlines the pull request (PR) process for MapsProveFiber contributions.

---

## 🎯 Before Creating a PR

### 1. Create an Issue First

- Describe the problem or feature
- Get feedback from maintainers
- Reference issue in PR

### 2. Branch from `inicial`

```powershell
git checkout inicial
git pull origin inicial
git checkout -b feat/your-feature-name
```

### 3. Follow Branch Naming

- `feat/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code restructuring
- `docs/` - Documentation updates
- `test/` - Test additions

---

## ✅ PR Checklist

Before submitting, ensure:

- [ ] **Tests pass**: `pytest -q` (199/199 passing)
- [ ] **Code formatted**: `make fmt`
- [ ] **Linting clean**: `make lint`
- [ ] **Type checks pass**: `make type-check` (if applicable)
- [ ] **Django check**: `python manage.py check`
- [ ] **Migrations created**: If models changed
- [ ] **Documentation updated**: For API/behavior changes
- [ ] **Changelog entry**: For user-facing changes
- [ ] **No merge conflicts**: Rebase if needed

---

## 📝 PR Description Template

```markdown
## Description
Brief summary of changes.

## Related Issue
Fixes #123

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?
- [ ] Unit tests added/updated
- [ ] Manual testing performed
- [ ] Smoke tests passing

## Screenshots
If UI changes, include before/after screenshots.

## Checklist
- [ ] Code follows style guide
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No breaking changes (or documented in BREAKING_CHANGES.md)
```

---

## 🔍 Review Process

### 1. Automated Checks

CI/CD runs automatically:
- Tests (pytest)
- Linting (ruff, black)
- Type checking
- Security scanning

### 2. Code Review

Reviewers check:
- Code quality and style
- Test coverage
- Documentation
- Security implications
- Performance impact

### 3. Approval Requirements

- **1 approval** for docs/tests
- **2 approvals** for features/refactors
- **All approvals** for breaking changes

---

## 🚀 Merging Strategy

### Merge Methods

- **Squash and merge**: Default for most PRs
- **Rebase and merge**: For clean commit history
- **Merge commit**: For feature branches with multiple logical commits

### After Merge

1. Delete branch (done automatically)
2. Update related issues
3. Update documentation if needed
4. Monitor for issues

---

## 🐛 Fixing Review Feedback

### Update PR

```powershell
# Make changes
git add .
git commit -m "fix: address review comments"
git push origin feat/your-feature

# Or amend last commit
git add .
git commit --amend --no-edit
git push --force-with-lease origin feat/your-feature
```

### Resolve Conflicts

```powershell
git checkout inicial
git pull origin inicial
git checkout feat/your-feature
git rebase inicial

# Resolve conflicts, then:
git add .
git rebase --continue
git push --force-with-lease origin feat/your-feature
```

---

## 📏 Size Guidelines

### Keep PRs Small

- **Ideal**: < 400 lines changed
- **Maximum**: < 1000 lines
- Large changes: Split into multiple PRs

### Breaking Up Large Changes

1. Refactoring PR (no behavior change)
2. Tests PR (if needed)
3. Feature implementation PR
4. Documentation PR

---

## 🏷️ Labeling

Apply appropriate labels:

- `bug` - Bug fixes
- `enhancement` - New features
- `documentation` - Docs only
- `breaking-change` - Breaking changes
- `needs-review` - Ready for review
- `work-in-progress` - Not ready
- `blocked` - Blocked by other work

---

## 🔄 Draft PRs

Use draft PRs for:
- Work in progress
- Getting early feedback
- CI/CD validation

Convert to ready when:
- All changes complete
- Tests passing
- Ready for review

---

## 📚 Examples

### Good PR Titles

✅ `feat(inventory): add KML import for fiber cables`  
✅ `fix(monitoring): handle missing Zabbix hosts`  
✅ `docs: update API authentication guide`  
✅ `refactor(core): extract health check logic`

### Bad PR Titles

❌ `Update code`  
❌ `Fix bug`  
❌ `Changes`  
❌ `WIP`

---

## 🚫 Common Mistakes

### Avoid

- Large, unfocused PRs
- Missing tests
- Unformatted code
- Merge conflicts
- Breaking changes without notice
- Missing documentation
- Commented-out code
- Debug statements

---

## 📞 Getting Help

- Ask questions in PR comments
- Tag reviewers: `@username`
- Reach out in team chat
- Check existing PRs for examples

---

## 📚 Resources

- [Code Style Guide](CODE_STYLE.md)
- [Testing Standards](TESTING_STANDARDS.md)
- [Contributing Guide](README.md)

---

**Last Updated**: 2025-11-10
