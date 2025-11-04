# Internationalization and PR Checklist

Status: Accepted - 2025-10-28  
Applies to: Backend (Django), Frontend (Fiber Route Builder and Dashboard), Documentation

---

## 1. Language Baseline

- **Source language:** English for code comments, log messages, UI defaults, docs, and commit messages.
- **Legacy strings:** When Portuguese wording is still required (for compatibility or user copy), mark the TODO in the file header and open a tracking ticket.
- **Secrets/logs:** Never translate or expose sensitive data when converting strings.

## 2. Django (Backend) Guidelines

1. Wrap user-facing strings with `gettext` / `gettext_lazy` (`from django.utils.translation import gettext as _`).
2. Add or update translation files with `django-admin makemessages -l <locale>` and commit the `.po` changes.
3. Keep message contexts (`pgettext`) when the same word appears with distinct meanings.
4. When logging, prefer structured context (e.g. `logger.info("fiber_created", fiber_id=fiber.id)`) and keep messages in English.

## 3. Frontend (JS / Templates)

1. **Static templates:** Use `{% trans %}` or `{% blocktrans %}` for strings rendered via Django templates.
2. **JavaScript modules:**
   - Centralise strings in a `translations` object injected via template context (`window.i18n`).
   - Include an English fallback; avoid hard-coded Portuguese in modules.
3. **Fiber Route Builder:** Follow the conventions documented in `./adr_fiber_route_builder.md`.
4. Document any new strings in the product copy sheet (`./i18n_copy_catalog.md`, to be created when translations are added).

## 4. Testing Requirements

- Add/extend tests when a string change could affect behaviour (e.g., selectors or conditional logic).
- For jest tests, mock `window.i18n` where needed.
- For Django views, assert translated output using `override_settings(LANGUAGE_CODE="...")`.

## 5. PR Checklist (to be included in every review)

Before opening a pull request, confirm:

1. [ ] Strings, comments, and logs introduced in this PR are written in English.
2. [ ] New user-facing strings are wrapped in the appropriate translation helper (`gettext`, `{% trans %}`, or JS translation layer).
3. [ ] Tests were added or updated to cover the change (`pytest`, `npm test`, or manual QA steps documented).
4. [ ] Documentation or ADR updates included when architecture or conventions change.
5. [ ] `pre-commit` or lint commands were executed (`make lint`, `npm run lint` when applicable).

## 6. Suggested Workflow

1. Implement feature/fix using English defaults.
2. Identify strings that require localisation in the product; raise a follow-up issue if translation assets are missing.
3. Update ./ADR if new patterns emerge.
4. Run automated tests and linting.
5. Fill in the PR template checklist (see `.github/pull_request_template.md`).

Following this guideline keeps the codebase consistent, improves onboarding for non-Portuguese speakers, and prepares the project for future localisation initiatives.
