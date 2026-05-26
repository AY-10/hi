import { useEffect, useMemo, useState } from "react";
import dayjs from "dayjs";

type Summary = {
  total_rows: number;
  needs_review: number;
  approved: number;
  rejected: number;
  suspicious: number;
  locked: number;
};

type Organization = {
  id: number;
  name: string;
  slug: string;
};

type Source = {
  id: number;
  name: string;
  source_type: "sap" | "utility" | "travel";
  source_type_label: string;
  ingestion_mode_label: string;
  description: string;
};

type Batch = {
  id: number;
  file_name: string;
  raw_format: string;
  record_count: number;
  received_at: string;
  source_name: string;
};

type AuditEvent = {
  id: number;
  action: string;
  actor: string;
  note: string;
  created_at: string;
};

type RecordRow = {
  id: number;
  source_name: string;
  source_type: "sap" | "utility" | "travel";
  source_type_label: string;
  batch_file_name: string;
  source_record_id: string;
  record_kind:
    | "fuel"
    | "procurement"
    | "electricity"
    | "flight"
    | "hotel"
    | "ground_transport";
  record_kind_label: string;
  scope: "scope1" | "scope2" | "scope3";
  scope_label: string;
  activity_date: string;
  activity_value: string;
  activity_unit: string;
  normalized_value: string;
  normalized_unit: string;
  emissions_kg_co2e: string | null;
  confidence_score: number;
  suspicion_flags: string[];
  review_status: "staged" | "needs_review" | "approved" | "rejected" | "locked";
  review_status_label: string;
  review_note: string;
  source_payload: Record<string, unknown>;
  audit_events: AuditEvent[];
};

type DashboardResponse = {
  organization: Organization;
  summary: Summary;
  sources: Source[];
  recent_batches: Batch[];
  rows: RecordRow[];
};

const statusLabels: Record<RecordRow["review_status"], string> = {
  staged: "Staged",
  needs_review: "Needs review",
  approved: "Approved",
  rejected: "Rejected",
  locked: "Locked",
};

const sourceTone: Record<RecordRow["source_type"], string> = {
  sap: "sap",
  utility: "utility",
  travel: "travel",
};

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function formatValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const asNumber = Number(value);
  if (!Number.isNaN(asNumber) && String(value).trim() !== "") {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(
      asNumber,
    );
  }
  return String(value);
}

function badgeText(flags: string[]) {
  if (flags.length === 0) return "Clean";
  if (flags.length === 1) return "Review";
  return `${flags.length} flags`;
}

export default function App() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<
    "all" | RecordRow["review_status"]
  >("all");
  const [sourceFilter, setSourceFilter] = useState<
    "all" | RecordRow["source_type"]
  >("all");
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState({
    review_note: "",
    confidence_score: 0,
    normalized_value: "",
  });

  async function loadDashboard() {
    setBusy(true);
    setError(null);
    try {
      const payload = await fetchJson<DashboardResponse>("/api/dashboard/");
      setData(payload);
      setSelectedId((current) => current ?? payload.rows[0]?.id ?? null);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Failed to load dashboard",
      );
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const rows = data?.rows ?? [];
  const selected =
    selectedId === null
      ? null
      : rows.find((row) => row.id === selectedId) ?? null;

  useEffect(() => {
    if (selected) {
      setEditDraft({
        review_note: selected.review_note,
        confidence_score: selected.confidence_score,
        normalized_value: selected.normalized_value,
      });
    }
  }, [selected?.id]);

  const filteredRows = useMemo(() => {
    const query = search.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesStatus =
        statusFilter === "all" || row.review_status === statusFilter;
      const matchesSource =
        sourceFilter === "all" || row.source_type === sourceFilter;
      const haystack = [
        row.source_name,
        row.source_record_id,
        row.record_kind_label,
        row.scope_label,
        row.activity_date,
        row.review_note,
        row.batch_file_name,
        ...row.suspicion_flags,
      ]
        .join(" ")
        .toLowerCase();
      const matchesQuery = query.length === 0 || haystack.includes(query);
      return matchesStatus && matchesSource && matchesQuery;
    });
  }, [rows, search, sourceFilter, statusFilter]);

  useEffect(() => {
    if (filteredRows.length === 0) {
      setSelectedId(null);
      return;
    }

    const selectedStillVisible = filteredRows.some(
      (row) => row.id === selectedId,
    );

    if (!selectedStillVisible) {
      setSelectedId(filteredRows[0].id);
    }
  }, [filteredRows, selectedId]);

  const filterSummary = `${filteredRows.length} of ${rows.length} rows shown`;
  const filterActive =
    search.trim().length > 0 || statusFilter !== "all" || sourceFilter !== "all";

  async function runAction(path: string, body: Record<string, unknown> = {}) {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await fetchJson<RecordRow>(path, {
        method: "POST",
        body: JSON.stringify({ actor: "analyst", ...body }),
      });
      await loadDashboard();
    } catch (actionError) {
      setError(
        actionError instanceof Error ? actionError.message : "Action failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function saveEdits() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await fetchJson<RecordRow>(`/api/records/${selected.id}/`, {
        method: "PATCH",
        body: JSON.stringify({
          actor: "analyst",
          review_note: editDraft.review_note,
          confidence_score: editDraft.confidence_score,
          normalized_value: editDraft.normalized_value,
          note: "Edited from the review drawer.",
        }),
      });
      await loadDashboard();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function seedDemo() {
    setBusy(true);
    setError(null);
    try {
      await fetchJson<DashboardResponse>("/api/seed-demo/", {
        method: "POST",
        body: "{}",
      });
      await loadDashboard();
    } catch (seedError) {
      setError(
        seedError instanceof Error ? seedError.message : "Seeding failed",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <div className="background-grid" />
      <div className="glow glow-a" />
      <div className="glow glow-b" />
      <header className="hero">
        <div>
          <p className="eyebrow">Breathe ESG review workspace</p>
          <h1>
            Normalize messy client emissions data before it reaches audit.
          </h1>
          <p className="hero-copy">
            Demo tenant: SAP fuel/procurement exports, utility bills, and
            Concur-style travel rows are normalized into a single analyst queue
            with provenance and audit history.
          </p>
        </div>
        <div className="hero-actions">
          <button
            className="button secondary"
            onClick={loadDashboard}
            disabled={busy}
          >
            Refresh dashboard
          </button>
          <button className="button primary" onClick={seedDemo} disabled={busy}>
            Load demo data
          </button>
        </div>
      </header>

      {error ? <div className="alert">{error}</div> : null}

      <section className="summary-grid">
        <StatCard
          label="Rows ingested"
          value={data?.summary.total_rows ?? 0}
          tone="slate"
        />
        <StatCard
          label="Needs review"
          value={data?.summary.needs_review ?? 0}
          tone="amber"
        />
        <StatCard
          label="Approved"
          value={data?.summary.approved ?? 0}
          tone="green"
        />
        <StatCard
          label="Suspicious"
          value={data?.summary.suspicious ?? 0}
          tone="crimson"
        />
      </section>

      <section className="source-strip">
        <div className="source-strip-card">
          <span className="detail-label">Filtered view</span>
          <strong>{filterSummary}</strong>
          <p>
            {filterActive
              ? "Filters are applied to the review queue only, so analysts can focus on one slice at a time."
              : "All seeded rows are visible. Use the filters to narrow the queue."}
          </p>
        </div>
        <div className="source-strip-card compact">
          <span className="detail-label">Sources in scope</span>
          <div className="source-pills">
            <span>SAP</span>
            <span>Utility</span>
            <span>Travel</span>
          </div>
        </div>
        <div className="source-strip-card compact">
          <span className="detail-label">Audit state</span>
          <div className="source-pills muted">
            <span>Provenance</span>
            <span>Normalization</span>
            <span>Sign-off</span>
          </div>
        </div>
      </section>

      <section className="subgrid">
        <article className="panel queue-panel">
          <div className="panel-heading">
            <div>
              <p className="panel-kicker">Review queue</p>
              <h2>Rows waiting for analyst sign-off</h2>
            </div>
            <div className="filter-row">
              <label className="field search-field">
                <span>Search rows, flags, or batch name</span>
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search rows, flags, or batch name"
                />
              </label>
              <label className="field">
                <span>All statuses</span>
                <select
                  value={statusFilter}
                  onChange={(event) =>
                    setStatusFilter(event.target.value as typeof statusFilter)
                  }
                >
                  <option value="all">All statuses</option>
                  {Object.entries(statusLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>All sources</span>
                <select
                  value={sourceFilter}
                  onChange={(event) =>
                    setSourceFilter(event.target.value as typeof sourceFilter)
                  }
                >
                  <option value="all">All sources</option>
                  <option value="sap">SAP</option>
                  <option value="utility">Utility</option>
                  <option value="travel">Travel</option>
                </select>
              </label>
            </div>
          </div>

          <div className="queue-list">
            {filteredRows.map((row) => {
            {filteredRows.length === 0 ? (
              <div className="empty-queue">
                <h3>No rows match the current filters.</h3>
                <p>Clear search or filters to bring the queue back.</p>
              </div>
            ) : null}
              const isSelected = row.id === selected?.id;
              return (
                <button
                  className={`queue-row ${isSelected ? "selected" : ""}`}
                  key={row.id}
                  onClick={() => setSelectedId(row.id)}
                >
                  <div className="row-main">
                    <div
                      className={`source-pill ${sourceTone[row.source_type]}`}
                    >
                      {row.source_type_label}
                    </div>
                    <div>
                      <div className="row-title">
                        {row.record_kind_label} · {row.source_record_id}
                      </div>
                      <div className="row-meta">
                        {row.source_name} ·{" "}
                        {dayjs(row.activity_date).format("D MMM YYYY")} ·{" "}
                        {row.scope_label}
                      </div>
                    </div>
                  </div>
                  <div className="row-side">
                    <span className={`status-pill ${row.review_status}`}>
                      {statusLabels[row.review_status]}
                    </span>
                    <strong>
                      {formatValue(row.emissions_kg_co2e)} kg CO2e
                    </strong>
                    <span>{badgeText(row.suspicion_flags)}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </article>

        <article className="panel detail-panel sticky-panel">
          {selected ? (
            <>
              <div className="panel-heading compact">
                <div>
                  <p className="panel-kicker">Selected row</p>
                  <h2>{selected.record_kind_label}</h2>
                </div>
                <span className={`status-pill ${selected.review_status}`}>
                  {selected.review_status_label}
                </span>
              </div>

              <div className="detail-grid">
                <div className="detail-card">
                  <span className="detail-label">Source provenance</span>
                  <div>{selected.source_name}</div>
                  <div>{selected.batch_file_name}</div>
                  <div>Record {selected.source_record_id}</div>
                </div>
                <div className="detail-card">
                  <span className="detail-label">Normalization</span>
                  <div>
                    {formatValue(selected.activity_value)}{" "}
                    {selected.activity_unit}
                  </div>
                  <div>
                    {formatValue(selected.normalized_value)}{" "}
                    {selected.normalized_unit}
                  </div>
                  <div>{formatValue(selected.emissions_kg_co2e)} kg CO2e</div>
                </div>
                <div className="detail-card">
                  <span className="detail-label">Flags</span>
                  <div>
                    {selected.suspicion_flags.length
                      ? selected.suspicion_flags.join(", ")
                      : "None"}
                  </div>
                  <div>Confidence {selected.confidence_score}%</div>
                  <div>{selected.scope_label}</div>
                </div>
              </div>

              <div className="mini-metrics">
                <div className="mini-metric">
                  <span>Activity</span>
                  <strong>{selected.activity_unit}</strong>
                </div>
                <div className="mini-metric">
                  <span>Emissions</span>
                  <strong>{formatValue(selected.emissions_kg_co2e)} kg</strong>
                </div>
                <div className="mini-metric">
                  <span>Confidence</span>
                  <strong>{selected.confidence_score}%</strong>
                </div>
              </div>

              <div className="form-card">
                <label>
                  Review note
                  <textarea
                    value={editDraft.review_note}
                    onChange={(event) =>
                      setEditDraft((draft) => ({
                        ...draft,
                        review_note: event.target.value,
                      }))
                    }
                    rows={4}
                  />
                </label>
                <div className="inline-fields">
                  <label>
                    Confidence score
                    <input
                      type="number"
                      value={editDraft.confidence_score}
                      onChange={(event) =>
                        setEditDraft((draft) => ({
                          ...draft,
                          confidence_score: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                  <label>
                    Normalized value
                    <input
                      value={editDraft.normalized_value}
                      onChange={(event) =>
                        setEditDraft((draft) => ({
                          ...draft,
                          normalized_value: event.target.value,
                        }))
                      }
                    />
                  </label>
                </div>
                <div className="action-row">
                  <button
                    className="button secondary"
                    onClick={() =>
                      runAction(`/api/records/${selected.id}/flag/`, {
                        flag: "manual_review",
                      })
                    }
                    disabled={busy}
                  >
                    Flag
                  </button>
                  <button
                    className="button secondary"
                    onClick={() =>
                      runAction(`/api/records/${selected.id}/reject/`, {
                        note: editDraft.review_note,
                      })
                    }
                    disabled={busy}
                  >
                    Reject
                  </button>
                  <button
                    className="button primary"
                    onClick={saveEdits}
                    disabled={busy}
                  >
                    Save edits
                  </button>
                  <button
                    className="button success"
                    onClick={() =>
                      runAction(`/api/records/${selected.id}/approve/`, {
                        note: editDraft.review_note,
                      })
                    }
                    disabled={busy}
                  >
                    Approve and lock
                  </button>
                </div>
              </div>

              <div className="payload-card">
                <h3>Raw source payload</h3>
                <pre>{JSON.stringify(selected.source_payload, null, 2)}</pre>
              </div>

              <div className="timeline-card">
                <h3>Audit trail</h3>
                <div className="timeline">
                  {selected.audit_events.map((event) => (
                    <div key={event.id} className="timeline-item">
                      <strong>{event.action}</strong>
                      <span>{event.actor}</span>
                      <p>{event.note}</p>
                      <time>
                        {dayjs(event.created_at).format("D MMM YYYY, HH:mm")}
                      </time>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <h2>No row selected</h2>
              <p>
                Load the demo dataset, then pick a row to inspect the
                provenance, suspicious flags, and audit trail.
              </p>
            </div>
          )}
        </article>
      </section>
    </main>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "slate" | "amber" | "green" | "crimson";
}) {
  return (
    <div className={`stat-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
