# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`

**Created**: [DATE]

**Status**: Draft <!-- Draft → In Review → Approved -->

**Input**: User description: "$ARGUMENTS"

## Review & Approval *(mandatory before plan)*

<!--
  Constitution Governance ("승인 주체"): approval means an adversarial review by a
  session/model SEPARATE from the author, with the result recorded here, followed
  by explicit approval. Self-approval within the same session does not satisfy this.
-->

- **Reviewer** (separate session/model — may be an AI model): [name or model]
- **Reviewed at**: [DATE]
- **Review evidence**: [link to review notes / findings, or inline summary]
- **Approval** (final approver MUST be a human — Principle XIX): [ ] Approved for planning — [human approver, DATE]

## Business Context *(mandatory)*

<!--
  Constitution Principle XVIII (Learning-Oriented Documentation): every spec
  must capture the business "why", not just the functional "what".
-->

[Why does this feature need to exist from a business/commerce perspective? What problem does it solve for shoppers, vendors, or operators? Reference the affected domain(s) per Principle III/VIII, e.g., Catalog, Inventory, Order, Shipment, Promotion, Settlement.]

## Domain Concepts *(mandatory)*

<!--
  Name the business concepts this feature introduces or touches, independent
  of implementation. Keep these technology-agnostic (no table/class names).
-->

- **[Concept 1]**: [Plain-language definition of the business concept]
- **[Concept 2]**: [How it relates to existing domain concepts]

## Business Rules *(mandatory)*

<!--
  Constraints the business imposes, independent of how they get implemented.
  If a rule touches Promotion (Principle X) or immutable order snapshots
  (Principle IV), call that out explicitly.
-->

- [Rule 1, e.g., "A vendor's inventory reservation MUST expire after 15 minutes if unpaid"]
- [Rule 2]

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Architectural Considerations *(mandatory)*

<!--
  Constitution alignment check for this feature. Flag anything relevant;
  mark "N/A" for principles that do not apply to this feature.
-->

- **Domain ownership** (Principle VII/VIII): [Which Django app(s)/domain(s) own this feature's data and rules?]
- **External systems** (Principle IX): [Does this feature touch Payment, Point, ERP, Email, SMS, or Push, including read-only access? If so, note the Gateway/ACL boundary and keep every gateway call outside an open DB transaction; when an external category has multiple vendors, note the one common domain-facing interface + vendor-specific adapters. Otherwise N/A.]
- **Immutable snapshots** (Principle IV): [Does this feature produce or consume order-time snapshot data? If so: what is frozen and the named transition that freezes it (e.g., OrderPlaced); the decision inputs captured alongside; freeze-before-payment and comparison of externally-notified payment amounts against the frozen total; no recalculation from live data; historical reproducibility even after prices/promotions/points change; and frozen settlement/fulfilment classification (e.g., consignment vs direct-buy) without proxy inference. If the frozen order can sit unpaid, specify its validity period and expiry handling (independent of any resource reservation). Otherwise N/A.]
- **PII in snapshots** (Principle IV): [If snapshots/audit records contain personal data, note the retention/purge policy and separation-or-masking approach; otherwise N/A.]
- **Promotion policy** (Principle X): [If this feature introduces or changes a promotion: stacking rules & priority, calculation order, funding party (platform vs vendor) & settlement reflection, cap/budget policy. Otherwise N/A.]
- **Domain events** (Principle XII): [What domain events, if any, does this feature emit or consume? For every event define the envelope (unique event ID, occurred-at timestamp, aggregate/target ID), classify dispatch as same-transaction synchronous or durable cross-process/async, and keep the publishing API decoupled from dispatch. Otherwise N/A.]
- **Cross-domain interfaces** (Principle VIII): [What other domains does this feature call into, and via what interface? Do cross-domain references use IDs by default? Any direct cross-domain FK is explicitly justified here (Principle VIII SHOULD).]
- **Money & correctness** (Principle V): [Does this feature compute or store money? Confirm Money type and rounding rules; otherwise N/A.]
- **Idempotency & delivery** (Principle XIII): [Does it move money, mutate inventory, cause an external side effect, or emit/consume a cross-process/async domain event? Note idempotency keys. Read-only external integration triggers Principle IX but not XIII's idempotency/reliable-delivery contract. **Durable events only**: specify at-least-once delivery, consumer tolerance of duplicate & out-of-order delivery, and the retry limit + poison-message isolation/owner alert; same-transaction synchronous handlers do not require outbox, duplicate/out-of-order handling, or dead-letter infrastructure. **State-changing external calls**: commit intent → external call → record result; any outbox row is written in the originating transaction; required delivery uses outbox/persisted intent, not `on_commit`. Otherwise N/A.]
- **Reverse flows** (Principle XI): [How do cancel/return/refund and partial (per-item, per-vendor) scope apply? Decide: benefit (coupon/point/promotion) restore-or-reclaim incl. expired benefits, per-line/per-vendor allocation of order-level discounts & shipping and remainder handling, promotion re-evaluation on partial cancel, refund method & order. Results are append-only facts referencing the immutable original snapshot (never edit the original). As seller-of-record the platform's refund duty is independent of vendor cooperation/solvency. Model settlement offset / negative balance / carry-over / unrecovered-receivable and payout hold. For vendor-fault refunds, note settlement offset/hold. Or state why out of scope.]
- **Vendor isolation** (Principle VI): [What actor roles apply, and how is cross-vendor access prevented?]
- **Operator intervention** (Principle VI): [What admin actions correct/mediate/act-on-behalf for exceptions, and what audit trail (actor, reason, evidence) do they leave? N/A if none.]
- **Vendor lifecycle** (Principle III): [If this touches vendors, what do lifecycle states (screening/active/suspended/wound-down) imply for catalog exposure, new orders, and settlement? Map vendor ownership across catalog/inventory/order/settlement, and treat wind-down as settling residual obligations (open orders, unsettled balances, statutory return periods), not immediate deletion. Otherwise N/A.]
- **Audit trail** (Principle XV-감사, universal): [Every change to money, inventory, order state, and vendor state MUST leave an immutable audit record answering "why is this value what it is now" — note where it is written. Applies even when no external system is involved.]
- **Reconciliation** (Principle XV-대사, external only): [For money/inventory crossing an external boundary: what reconciles against external records, which external correlation IDs are stored, and the gateway raw-record + masking/retention. **Delivery stage**: reconciliation operated now or deferred to go-live? Note owner + follow-up task ID.]
- **Observability & detection** (Principle XVI): [What automatic/scheduled state changes occur, and how are anomalies alerted to the responsible owner? What is the target time-to-detect? **Delivery stage**: alert channel + TTD operated now or deferred to go-live? Note owner + follow-up task ID.]
- **In-flight reservations** (Principle XIV): [Does this feature hold resources (inventory, points, ticket stock) before a transaction confirms? Note the reserve→confirm/release flow (cancellation is a command that triggers release, not a separate state), expiry, timeout fallback policy, and how concurrent reservations are serialized (DB-level invariant) and confirm/release made atomic to prevent oversell/double-sell. Commit only from the authoritative source (reservation in the system of record, not a cache/projection), and avoid Saga/distributed-transaction engines until a measured need is proven. Otherwise N/A.]
- **Forward exposure consistency**: [When displayed price/availability differs from the order-time applied value, which value wins and how is the customer notified? N/A if not customer-facing.]
- **Evidence & legacy** (Principle XVII): [If this reuses legacy (shop/store) logic, how was it independently re-specified and tested rather than assumed correct?]
- **Standard state model** (Governance): [Which order/shipment/claim states & transitions does this feature use? Reference the single standard state-model doc; if it adds/changes a state, note the required doc amendment. N/A if it touches no such state.]
- **Schema & contract evolution** (Principle IV / constraints): [Do frozen snapshots carry a schema-version marker and do domain event payloads carry a version, with readers handling all historical versions and migrations not rewriting frozen snapshots? Are event payload changes backward-compatible by default, and do zero-downtime migrations use expand-contract? N/A if no snapshot/event.]
- **Scope boundaries** (Governance / range constraint): [Explicitly name any domain intentionally left out of scope (e.g., Cart, Customer/Membership, Vendor lifecycle) so it is not silently absorbed into Order. Required — state "none excluded" if nothing is deferred.]

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- [Assumption about target users, e.g., "Users have stable internet connectivity"]
- [Assumption about scope boundaries, e.g., "Mobile support is out of scope for v1"]
- [Assumption about data/environment, e.g., "Existing authentication system will be reused"]
- [Dependency on existing system/service, e.g., "Requires access to the existing user profile API"]
