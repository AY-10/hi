# MODEL

The prototype uses one normalized fact table, `ReviewRecord`, instead of keeping separate tables per source. That keeps the analyst workflow simple: every incoming row, regardless of SAP, utility, or travel origin, lands in the same queue with enough source context to defend how it was derived.

## Tenancy

`Organization` is the tenant boundary. Every source, batch, and review row points back to exactly one organization. The current app seeds one demo tenant, but the schema is shaped for multiple tenants without changing the core workflow.

## Source of truth

`SourceSystem` tracks where the row came from and how it was ingested. `IngestionBatch` stores the file/feed identity, raw format, and received time. `ReviewRecord` stores the immutable source payload in `source_payload`, the source row id, row number, and source update timestamp. That gives a clear answer to: what arrived, from where, and when.

## Normalization

Each row stores both the original activity value/unit and the normalized activity value/unit. In this prototype the normalized unit is category-specific, not a single universal unit:

`fuel` -> liters
`electricity` -> kWh
`flight` and `ground_transport` -> km
`hotel` -> nights
`procurement` -> spend currency

That is enough to compare and review rows without pretending all ESG inputs are the same physical quantity. Emissions are stored separately as `emissions_kg_co2e` so the analyst can inspect both the activity data and the derived carbon output.

## Scope mapping

The `scope` field is explicit on every row. The prototype maps:

`fuel` -> Scope 1
`electricity` -> Scope 2
`procurement`, `flight`, `hotel`, `ground_transport` -> Scope 3

This is intentionally opinionated and visible. If the PM wanted a different accounting policy, this is the field I would expect to change.

## Review and audit trail

`ReviewRecord.review_status` tracks the analyst state: staged, needs review, approved, rejected, or locked. `approved_by`, `approved_at`, `locked_at`, and `version` show when a row was finalized and whether it was edited after import.

`AuditEvent` stores before and after snapshots for imports, edits, approvals, rejections, and flags. That gives the reviewer a full trail without needing to reconstruct state from application logs.

## Suspicion and quality flags

`suspicion_flags` is a JSON list because the reasons are heterogeneous: missing destination airport, non-positive consumption, estimated values, or unusually large spend/usage. The UI can show these as reviewer cues without normalizing them into a rigid relational schema too early.
