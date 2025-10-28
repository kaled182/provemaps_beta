# ADR: Fiber Route Builder Conventions

## Status
Accepted – 2025-10-28

## Context
The Fiber Route Builder frontend was recently modularised into ES module helpers
(`mapCore`, `pathState`, `cableService`, `uiHelpers`, `modalEditor`, etc.). During
the refactor several comments, log messages, and UI strings remained in
Portuguese. That mix of languages makes onboarding harder, breaks searchability,
and complicates future localisation efforts. We also want a single place to
document how the builder modules interact, which module owns which piece of
state, and the expected naming conventions for new code.

## Decision
1. **Language standard** – code comments, inline messages, log entries, and UI
   defaults in the builder must be written in English. Portuguese wording is
   only retained inside legacy compatibility stubs or user-configurable content.
2. **Module boundaries** – keep the current three-layer separation:
   `pathState` (state management), `mapCore`/`cableService` (map primitives and
   backend orchestration), and `uiHelpers`/`modalEditor` (presentation logic).
   New behaviour should extend the relevant module instead of adding ad-hoc
   helpers inside `fiber_route_builder.js`.
3. **Public surface** – `fiber_route_builder.js` remains the orchestrator. It
   may expose functions that other scripts import, but those functions must
   delegate to module APIs and avoid reimplementing module logic.
4. **Naming conventions** – use lowerCamelCase for functions, UPPER_SNAKE_CASE
   for constants, and descriptive names for DOM hooks (e.g. `toastHost`,
   `contextSaveNewCable`). Avoid prefixes in Portuguese; favour words such as
   `reload`, `refresh`, `visualization`.
5. **Documentation & tests** – any new capability in the builder should include:
   * module-level JSDoc describing the responsibility,
   * an entry in this ADR if it changes architectural boundaries, and
   * tests (unit or integration) verifying the behaviour via mocks.

## Consequences
- Developers have a single reference that explains how to extend the builder and
  which modules they should touch.
- Future translation/internationalisation work can rely on English as the base
  language and gradually introduce proper i18n tooling.
- Pull requests can be reviewed against this ADR, ensuring new code follows the
  established module layering and naming rules.

