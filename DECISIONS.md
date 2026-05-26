# DECISIONS

## What I chose to build

I built a compact Django REST backend and a React review dashboard. The core object is a normalized review row with source provenance, editable review fields, and an audit trail.

## Ambiguities I resolved

### SAP

I modeled SAP as a flat-file style export rather than a live ERP integration. In practice that is the lowest-friction shape for an enterprise onboarding prototype and matches what finance/logistics teams usually hand over first.

I also treated SAP as a mixed feed: some rows are fuel, some are procurement. That reflects the reality that SAP exports often need downstream categorization before they are analytically useful.

### Utility

I chose a portal CSV / interval-data style export for electricity. That is a realistic shape for facilities teams because it exposes meter ids, billing periods, and consumption values without needing PDF OCR for the first prototype.

### Travel

I modeled travel as a Concur-style API feed. That gives a believable shape for trip id, category, airport codes, hotel nights, and ground transport distances while keeping the prototype workable without a real vendor connection.

## What I would ask the PM

I would ask three things:

1. Do you want the first version to prioritize upload parsing or review workflow?
2. Should procurement be treated as spend-based Scope 3 only, or do you want supplier-specific factors too?
3. What is the company’s actual source of truth for final approval: the analyst UI, the source system, or an export sent to auditors?

## What I intentionally ignored

I did not build authentication, role-based access control, or a full multi-tenant org admin experience. I also did not build real SAP/utility/travel integrations because the assignment asked for a realistic prototype, not a vendor-certified connector.
