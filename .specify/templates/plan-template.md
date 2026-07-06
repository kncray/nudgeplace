# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: The Initial Check MUST pass before Phase 0 research; the Post-Design Re-check MUST pass after Phase 1 design. Record both separately so each gate is auditable.*

Two-tier gate per Constitution governance: (1) CORE gates — I, III, IV, V, VI, VII, VIII — always evaluated; a core gate that genuinely does not apply remains visible and is recorded as N/A with rationale. (2) CONDITIONAL gates use the Constitution's single-source trigger matrix exactly: any external-system integration, including read-only → IX; money movement / inventory change / external side effect → XIII; any domain event → XII + XIII common event contract (identity/timestamp/aggregate ID and publishing/dispatch separation); cross-process or async domain event → XIII durable-delivery contract; resource pre-emption before commit → XIV; any change to money/inventory/order/vendor state → XV-감사; money/inventory crossing an external boundary → XV-대사; significant business state change → XII; automatic/scheduled state change → XVI; promotion → X; reverse flows → XI; legacy reuse → XVII. Evaluate only the core + triggered gates; do not mechanically re-evaluate all 20 principles.

### Initial Check (before Phase 0)

**Date**: [DATE]

| Gate (core + triggered) | Result (pass / fail / N/A) | Notes / justification; N/A requires rationale |
|---|---|---|
| | | |

### Post-Design Re-check (after Phase 1)

**Date**: [DATE]

| Gate | Result (pass / fail / N/A) | What changed since Initial Check; N/A requires rationale |
|---|---|---|
| | | |

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Django Modular Monolith (DEFAULT — Constitution Principle VII/VIII)
# One isolated Django app per business domain; cross-domain access only via
# each app's services.py / events, never another app's models directly.
apps/
├── <domain_name>/            # e.g., catalog, inventory, order, promotion, settlement
│   ├── models.py
│   ├── services.py           # public interface other domains call into
│   ├── events.py             # domain events emitted (Principle XII)
│   ├── gateways/              # ACL modules for external systems, if any (Principle IX)
│   ├── api.py
│   └── admin.py
└── <another_domain>/
    └── ...

tests/
├── <domain_name>/
│   ├── contract/
│   ├── integration/
│   └── unit/
└── ...

# [REMOVE IF UNUSED] Option 2: Single project (non-Django) — prototype/spike ONLY;
# production starts as Option 1 (Django modular monolith, Principle VII). A domain
# MAY later be extracted into a SEPARATE Django service once stable-boundary
# evidence + measured operational need are documented (Structure Decision + ADR);
# a non-Django rewrite is never a production option. Any deviation goes in
# Complexity Tracking.
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 3: Web application (Django backend + separate frontend)
# The backend MUST start as a Django modular monolith (Principle VII) — same
# apps/<domain>/ layout as Option 1, never a generic src/ backend; a domain may
# later be extracted to a separate Django service under the same documented
# justification as Option 1 (Structure Decision + ADR).
backend/
├── apps/
│   └── <domain_name>/        # models.py, services.py, events.py, gateways/, api.py
└── tests/
    └── <domain_name>/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 4: Mobile + API (when "iOS/Android" detected)
# The API backend is the Django modular monolith from Option 1 (apps/<domain>/).
api/
└── [Django backend as in Option 1: apps/<domain_name>/ + tests/<domain_name>/]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above. The monolith is the start state, not a permanent
ceiling: extracting a domain into a separate Django service is permitted once
stable-boundary evidence and a measured operational need are documented here and
in an ADR (Principle VII "필요가 입증되기 전까지 도입 금지"). Non-Django remains
prototype/spike only.]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

## Architecture Decisions

> Record architecturally significant decisions (new domain, new external integration, new cross-domain interface, monolith→service extraction). Principle XX: rationale is MUST; an ADR under `docs/adr/` is the SHOULD-level mechanism.

| Decision | Rationale | Alternatives considered | Trade-offs accepted | Evolution path | ADR link |
|---|---|---|---|---|---|
| | | | | | |

## Review & Approval

<!--
  Constitution Governance ("승인 주체"): the plan (like the spec) is reviewed by a
  session/model SEPARATE from the author, recorded here, before proceeding to tasks.
  The adversarial review MAY be an AI model; the final approval MUST be a human (Principle XIX).
-->

- **Reviewer** (separate session/model — may be an AI model): [name or model]
- **Reviewed at**: [DATE]
- **Review evidence**: [link to review notes / findings, or inline summary]
- **Approval** (final approver MUST be a human — Principle XIX): [ ] Approved to proceed to tasks — [human approver, DATE]
