---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test tasks are MANDATORY for every feature and MUST precede implementation (Constitution Principle I: Spec → Plan → Tasks → Tests → Implementation; Principle XVII: claims of done/passing require observed evidence). Tests for NEW behavior are written first and MUST FAIL before implementation (RED-GREEN); characterization/regression tests that pin existing or legacy behavior (Principle XVII) MAY pass from the start. The specific test tooling and depth are decided in plan.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions
- **Test task IDs** use the target task's ID + `t` suffix (e.g., T005t precedes T005; T009ct precedes T009c) and run immediately before their target; **go-live tasks** use `GLnn`. A `t` test and its target are never `[P]` together (the target depends on the test).

## Path Conventions

- **Django Modular Monolith (DEFAULT)**: `apps/<domain_name>/`, `tests/<domain_name>/` — one Django app per business domain (Constitution Principle VII/VIII)
- **Single project (non-Django/prototype only)**: `src/`, `tests/` at repository root — spike only, justify in Complexity Tracking
- **Web app**: Django backend `backend/apps/<domain>/` + `frontend/src/`
- **Mobile**: Django API `api/apps/<domain>/` + `ios/` or `android/`
- Sample tasks below use the Django Modular Monolith default (`apps/<domain>/`, `tests/<domain>/`); adjust to the structure chosen in plan.md

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.

  The /speckit-tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  - Architectural Considerations from spec.md + the triggered principles in
    plan.md's Constitution Check (address each triggered principle with a task
    or existing evidence — see the Constitution Gate & Traceability section)
  - Whenever XV-대사 (external money/inventory boundary) or XVI is
    triggered: generate the matching Go-live readiness-gate rows, and Go-live
    Enablement tasks only where the control is missing or deferred (internal
    XV-감사 alone does not trigger the go-live gate)

  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment

  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

**⚠️ Tests-first**: Only genuinely non-behavioral scaffolding is exempt (T001–T003 project init/tooling, T006 routing skeleton, T009 env config). Every foundational task that implements observable behavior — auth/authz (T005), base entities with rules (T007), error-handling behavior (T008), and the runtime-behavioral T009c/d/e2/f/h/i — MUST be preceded by its own failing test task with its own sequential ID, and its implementation task MUST record that dependency. A test and the code it drives are NOT `[P]` with each other (the impl depends on the test). 'Define interface/strategy' tasks (T009a/b/e/j) are design artifacts, tested when their behavior is implemented.

Examples of foundational tasks (adjust based on your project):

- [ ] T004 Setup database schema and migrations framework
- [ ] T005t [P] Write failing tests for authentication/authorization rules — Constitution Principle I
- [ ] T005 Implement authentication/authorization framework (depends on T005t)
- [ ] T006 [P] Setup API routing and middleware structure
- [ ] T007t [P] Write failing tests for base entity invariants/rules — Constitution Principle I
- [ ] T007 Create base models/entities that all stories depend on (depends on T007t)
- [ ] T008t [P] Write failing tests for error-handling behavior — Constitution Principle I
- [ ] T008 Configure error handling and logging infrastructure (depends on T008t)
- [ ] T009 Setup environment configuration management
- [ ] T009a [P] Define Gateway/ACL interface(s) for any external system this feature touches (Payment, Point, ERP, Email, SMS, Push), including the correlation ID(s) to persist — design artifact — Constitution Principle IX. When an external category has multiple vendors (e.g., multiple ticketing vendors in one category), define ONE common domain-facing interface + vendor-specific adapters. Skip if no external system
- [ ] T009a2t [P] Write failing tests for gateway raw-record persistence with secret/PII masking & bounded retention — Constitution Principle I; skip unless a money/inventory boundary (Payment, Point, ERP) is touched
- [ ] T009a2 Implement gateway request/response audit raw-record persistence with masking/tokenization/encryption of payment secrets & PII and bounded retention/purge (depends on T009a2t) — Constitution Principle XV; only for money/inventory boundaries — Email/SMS/Push need only the ACL + correlation metadata
- [ ] T009b [P] Define domain event(s) this feature emits/consumes, classify each as synchronous same-transaction OR durable cross-process/async, and define the common envelope (unique event ID, occurred-at timestamp, aggregate/target ID) with a publishing API decoupled from dispatch — design artifact — Constitution Principle XII, XIII; skip if none
- [ ] T009b1t Write failing tests for the common event-envelope fields and publishing-API/dispatch separation — Constitution Principle I; skip if this feature emits/consumes no events
- [ ] T009b1 Implement the common event envelope and dispatch-independent publishing API (depends on T009b1t) — applies to synchronous and durable events — Constitution Principle XIII; skip if this feature emits/consumes no events
- [ ] T009b2 [P] For durable cross-process/async or external-side-effect events only, define the consumer contract: at-least-once delivery; duplicate & out-of-order tolerance; retry limit; poison-message isolation (dead-letter) and owner alert — design artifact — Constitution Principle XIII, XVI; skip for same-transaction-only events
- [ ] T009b2it Write failing tests for durable-consumer duplicate & out-of-order tolerance and retry exhaustion → dead-letter isolation + owner alerting — Constitution Principle I; skip for same-transaction-only events
- [ ] T009b2i Implement idempotent/out-of-order-safe durable consumption and poison-message (dead-letter) isolation with owner alerting (depends on T009b2it) — Constitution Principle XIII, XVI; skip for same-transaction-only events
- [ ] T009b3t Write failing tests for the applicable transaction boundary: every external call stays outside an open DB transaction; for state-changing external calls or cross-process events, the outbox/intent is persisted in the originating transaction and required delivery does not rely on `on_commit` — Constitution Principle I; skip if no external call and no cross-process event
- [ ] T009b3 Enforce the applicable transaction boundary: every external/gateway call stays outside an open DB transaction (Principle IX); for state-changing external calls use commit intent → external call → record result in a new transaction, and for cross-process events write the outbox row in the originating transaction; required delivery uses outbox/persisted intent, not `on_commit`; keep the event-publishing API decoupled from dispatch (depends on T009b3t) — Constitution Principle IX, XIII; skip if this feature makes no external call and emits no cross-process event
- [ ] T009ct [P] Write failing tests for Money arithmetic & rounding — Constitution Principle I; skip if no money
- [ ] T009c Establish Money type and rounding rules (depends on T009ct) — Constitution Principle V; skip if none
- [ ] T009dt [P] Write failing tests for idempotency-key enforcement (duplicate suppression) — Constitution Principle I; skip if there is no money movement, inventory mutation, or external side effect
- [ ] T009d Define and enforce idempotency-key strategy for money movement, inventory mutation, and external side-effect operations (depends on T009dt) — read-only external calls do not trigger this task — Constitution Principle XIII; skip if none
- [ ] T009e [P] Add an import-linter contract for domain boundaries AND wire it into CI so a boundary-violating build fails (add a violating fixture to prove the build fails), or link existing CI evidence — Constitution Principle VIII; skip if this feature introduces no new domain (Django app) or cross-domain dependency
- [ ] T009e2t [P] Write failing tests for vendor-scoped authorization (cross-vendor access denied) — Constitution Principle I; skip if none
- [ ] T009e2 Enforce vendor-scoped authorization at the service boundary (depends on T009e2t) — Constitution Principle VI; skip if this feature reads/writes no vendor-owned data
- [ ] T009ft Write failing tests for reserve→confirm/release + expiry, including concurrent confirm vs expiry-release — Constitution Principle I; skip if none
- [ ] T009f Implement reserve→confirm/release state machine + expiry for any resource held before a transaction confirms (inventory, points, ticket stock); model cancellation as a command/reason that triggers RELEASE, not a separate terminal state; confirm/commit ONLY from the authoritative source (the reservation in the system of record, never a cache/projection); do NOT introduce Saga/distributed-transaction infrastructure without measured justification (depends on T009ft) — Constitution Principle XIV; skip if none
- [ ] T009g [P] For any automatic/scheduled state change: design the observable signal now (structured log/event carrying owner, actor, reason) and add tests covering boundary, sign/direction, and time-unit cases for scheduled logic — the actual alert channel + time-to-detect metric operation is staged (SHOULD before go-live, MUST by go-live) — Constitution Principle XVI
- [ ] T009ht Write failing tests for the resource invariant (e.g., stock ≥ 0) and atomic, mutually-exclusive confirm/release (oversell/double-sell prevention) — Constitution Principle I; skip if none
- [ ] T009h Enforce resource invariants at the DB level and make reserve confirm/release atomic & mutually exclusive (depends on T009ht) — Constitution Principle XIV; skip if this feature holds no concurrent-contended resource
- [ ] T009it [P] Write failing tests for reading all historical snapshot/event schema versions — Constitution Principle I; skip if none
- [ ] T009i Add a schema/version marker to any frozen snapshot and a version to any domain event payload, and implement readers that handle all historical versions (migrations must not rewrite frozen snapshots); domain event payload changes are backward-compatible by default, and schema migrations use expand-contract for zero-downtime deploy (depends on T009it) — Constitution Principle IV, XIII & schema-evolution constraint; skip if this feature produces no snapshot or event
- [ ] T009j Reference the single standard state-model doc (`docs/domain/state-model.md`) for order/shipment/claim states & transitions; create it if absent, and if this feature adds/changes a state, amend that doc rather than defining states ad hoc — Constitution Governance (Standard State Model); skip if this feature touches no such state
- [ ] T009kt Write failing tests that a money/inventory/order/vendor-state change writes an immutable audit record (actor, reason, before→after) — Constitution Principle I; skip only if this feature changes none of these
- [ ] T009k Ensure every change to money, inventory, order state, or vendor state writes an immutable audit record (actor, reason, before→after) answering "why is this value what it is now" (depends on T009kt) — Constitution Principle XV (universal audit; distinct from the external reconciliation/raw records in T009a2); skip only if this feature changes none of these

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (MANDATORY — write FIRST, must FAIL before implementation) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Contract test for [endpoint] in tests/[domain]/contract/test_[name].py
- [ ] T011 [P] [US1] Integration test for [user journey] in tests/[domain]/integration/test_[name].py

### Implementation for User Story 1 (depends on T010–T011 being written and failing)

- [ ] T012 [P] [US1] Create [Entity1] model in apps/[domain]/models/[entity1].py
- [ ] T013 [P] [US1] Create [Entity2] model in apps/[domain]/models/[entity2].py
- [ ] T014 [US1] Implement [Service] in apps/[domain]/services.py (depends on T012, T013)
- [ ] T015 [US1] Implement [endpoint/feature] in apps/[domain]/api.py
- [ ] T016 [US1] Add validation and error handling
- [ ] T017 [US1] Add logging for user story 1 operations

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (MANDATORY — write FIRST, must FAIL before implementation) ⚠️

- [ ] T018 [P] [US2] Contract test for [endpoint] in tests/[domain]/contract/test_[name].py
- [ ] T019 [P] [US2] Integration test for [user journey] in tests/[domain]/integration/test_[name].py

### Implementation for User Story 2 (depends on T018–T019 being written and failing)

- [ ] T020 [P] [US2] Create [Entity] model in apps/[domain]/models/[entity].py
- [ ] T021 [US2] Implement [Service] in apps/[domain]/services.py
- [ ] T022 [US2] Implement [endpoint/feature] in apps/[domain]/api.py
- [ ] T023 [US2] Integrate with User Story 1 components (if needed)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (MANDATORY — write FIRST, must FAIL before implementation) ⚠️

- [ ] T024 [P] [US3] Contract test for [endpoint] in tests/[domain]/contract/test_[name].py
- [ ] T025 [P] [US3] Integration test for [user journey] in tests/[domain]/integration/test_[name].py

### Implementation for User Story 3 (depends on T024–T025 being written and failing)

- [ ] T026 [P] [US3] Create [Entity] model in apps/[domain]/models/[entity].py
- [ ] T027 [US3] Implement [Service] in apps/[domain]/services.py
- [ ] T028 [US3] Implement [endpoint/feature] in apps/[domain]/api.py

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Additional unit tests in tests/[domain]/unit/
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation (mandatory — Constitution Principle I)
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority (applies to the sequential strategy only; the parallel strategy runs stories concurrently once Foundational is done)

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (write first, must fail before implementation):
Task: "Contract test for [endpoint] in tests/[domain]/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/[domain]/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in apps/[domain]/models/[entity1].py"
Task: "Create [Entity2] model in apps/[domain]/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Constitution Gate & Traceability

*This is the tasks-level Constitution Check the governance requires before implementation begins ("모든 스펙, 계획, 작업 목록은 구현을 시작하기 전에 이 헌장을 기준으로 점검해야 한다"). Fill it after generating tasks; implementation MUST NOT start until every core/triggered principle is satisfied by a task or existing evidence, or is explicitly N/A with rationale. A Waiver is allowed only for an unavoidable violation recorded in plan.md's Complexity Tracking.*

Core gates (always evaluated) + any triggered conditional principles:

| Principle (core always; conditional if triggered) | Disposition | Task IDs / evidence link / N/A rationale |
|---|---|---|
| VII — Modular monolith / Django app per domain (core) | | |
| IV — Immutable snapshots (core) | | |
| VIII — Domain boundaries (core) | | |
| I — Tests precede implementation (core) | | |
| V — Money type & rounding (core) | | |
| VI — Vendor isolation & authorization (core) | | |
| [conditional, e.g., IX/XIII — External ACL, idempotency, delivery & transaction boundary] | | |
| [conditional, e.g., XIV — reserve→confirm/release, DB-level invariant] | | |
| [conditional, e.g., XV-감사 — universal immutable audit trail] | | |
| [conditional, e.g., XV-대사 — external reconciliation, correlation IDs, masked/retained raw records] | | |
| [conditional, e.g., XVI — signal/alert design for automatic state change] | | |

- **Disposition** is one of: **Task** (satisfied by new task IDs listed here), **Existing Evidence** (already satisfied by current CI/architecture/docs — link it), **N/A** (evaluated but genuinely not applicable — rationale required), or **Waiver** (ONLY for an unavoidable violation, justified in plan.md's Complexity Tracking).
- The six core gates (VII, IV, VIII, I, V, VI) MUST always appear with a disposition; every conditional principle triggered in plan.md's Constitution Check MUST also appear. A row with none of Task / Existing Evidence / N/A / Waiver is a gap that blocks implementation. N/A is not a waiver and MUST NOT be used for an applicable but inconvenient requirement.

---

## Go-live Enablement & Readiness

*Applies whenever XV-대사 (money/inventory crossing an EXTERNAL boundary) or XVI is triggered — whether the operational infrastructure is built now or deferred to go-live (Constitution "Go-live 게이트"). Mark each row **Applicable / N/A** independently: the reconciliation rows are Applicable ONLY for XV-대사 (external boundary) — a feature with only internal XV-감사 marks them N/A (its immutable audit trail is verified in normal tasks/tests, not here); the alert/TTD rows are Applicable only for XVI. Build/verify the Enablement tasks first, then pass the Readiness Gate. Each Enablement task is preceded by its own failing test task and the impl depends on it.*

### Go-live Enablement (implementation tasks — do before the gate)

- [ ] GL01t Write failing test for reconciliation catch-up (detects & closes a seeded gap) — Principle I; [Applicable / N/A]
- [ ] GL01 Build & schedule the automatic/periodic reconciliation batch with catch-up (depends on GL01t) — Principle XV-대사 (external boundary only); [Applicable / N/A]
- [ ] GL02t Write failing test that an anomalous/high-impact state change raises an alert — Principle I; [Applicable / N/A]
- [ ] GL02 Wire the alert channel(s) for anomalous/high-impact state changes (depends on GL02t) — Principle XVI; [Applicable / N/A]
- [ ] GL03t Write failing test that the time-to-detect metric emits on a detected anomaly — Principle I; [Applicable / N/A]
- [ ] GL03 Instrument the time-to-detect metric with a named owner (depends on GL03t) — Principle XVI; [Applicable / N/A]

### Go-live Readiness Gate (verification — MUST pass before real users/transactions)

- [ ] Reconciliation batch enabled and catch-up verified — [Applicable only for XV-대사 / external boundary; else N/A] [evidence]
- [ ] Test alert delivered to the owner — [Applicable / N/A] [evidence]
- [ ] time-to-detect metric live with a responsible owner — [Applicable / N/A] [owner + evidence]
- [ ] Human approval to go live (Principle XIX) — [human approver, DATE]

If neither XV-대사 (external boundary) nor XVI applies to this feature, mark the whole section **N/A** and note why (internal XV-감사 alone does not require this gate).
