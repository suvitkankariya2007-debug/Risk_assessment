import { useEffect, useMemo, useState } from "react";
import { Check, ChevronDown, ChevronUp, ChevronsUpDown, Copy, Download, Plus, X } from "lucide-react";
import { toast } from "sonner";

type TicketStatus = "OPEN" | "IN_PROGRESS" | "DONE";
type TicketPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
type StatusTab = "ALL" | TicketStatus;

type BacklogTicket = {
  id: string;
  finding: string;
  asset_id: string;
  business_unit: string;
  eal_impact_lakh: number;
  owner: string;
  priority: TicketPriority;
  status: TicketStatus;
  sla_hours_remaining: number;
  remediation_command: string;
  jira_key: string | null;
};

const STATUS_ORDER: TicketStatus[] = ["OPEN", "IN_PROGRESS", "DONE"];
const PRIORITY_ORDER: Record<TicketPriority, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
const ASSET_IMPACT_SUGGESTIONS: Record<string, number> = {
  "core-pay-db-01": 68,
  "pay-gw-03": 61,
  "corp-fs-02": 48,
  "cards-api-legacy": 22,
  "iam-sso-01": 19,
  "branch-pos-fleet": 16,
  "org-wide": 72,
};
const ASSET_OPTIONS = [
  { value: "core-pay-db-01", label: "core-pay-db-01 - Core Banking" },
  { value: "pay-gw-03", label: "pay-gw-03 - Payments" },
  { value: "corp-fs-02", label: "corp-fs-02 - Corporate IT" },
  { value: "cards-api-legacy", label: "cards-api-legacy - Cards & Lending" },
  { value: "iam-sso-01", label: "iam-sso-01 - Corporate IT" },
  { value: "branch-pos-fleet", label: "branch-pos-fleet - Cards & Lending" },
  { value: "org-wide", label: "org-wide - All BUs" },
];

const fmtImpact = (value: number) => `₹${value.toFixed(0)}L`;
const priorityColor: Record<TicketPriority, string> = {
  CRITICAL: "#ef858d",
  HIGH: "var(--gold)",
  MEDIUM: "#f2c86f",
  LOW: "#51d1a1",
};
const STATUS_LABEL: Record<TicketStatus, string> = {
  OPEN: "Open",
  IN_PROGRESS: "In progress",
  DONE: "Done",
};

const normalizeStatus = (status?: string): TicketStatus => {
  switch ((status ?? "").toUpperCase()) {
    case "IN_PROGRESS":
    case "IN PROGRESS":
    case "BLOCKED":
      return "IN_PROGRESS";
    case "DONE":
    case "RESOLVED":
      return "DONE";
    default:
      return "OPEN";
  }
};

const describeSla = (hours: number) => {
  if (hours > 48) {
    return { label: `${hours}h left`, className: "sla-pill sla-pill--good" };
  }
  if (hours >= 24) {
    return { label: `${hours}h left`, className: "sla-pill sla-pill--warning" };
  }
  return { label: `${hours}h left`, className: "sla-pill sla-pill--danger" };
};

export default function RemediationBacklog() {
  const [tickets, setTickets] = useState<BacklogTicket[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<BacklogTicket | null>(null);
  const [activeTab, setActiveTab] = useState<StatusTab>("ALL");
  const [showForm, setShowForm] = useState(false);
  const [sortKey, setSortKey] = useState<"finding" | "eal_impact_lakh" | "priority" | "status">("eal_impact_lakh");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [form, setForm] = useState({
    finding: "",
    asset_id: "core-pay-db-01",
    business_unit: "Core Banking",
    eal_impact_lakh: "68",
    owner: "",
    priority: "HIGH" as TicketPriority,
  });

  const fetchTickets = async (nextTab: StatusTab = activeTab) => {
    try {
      const query = nextTab === "ALL" ? "" : `?status=${encodeURIComponent(nextTab)}`;
      const response = await fetch(`/api/v1/backlog/tickets${query}`, {
        headers: { "Content-Type": "application/json" },
      });
      if (!response.ok) {
        throw new Error("Unable to load ticket backlog");
      }
      const data = (await response.json()) as BacklogTicket[];
      setTickets(data.map((ticket) => ({ ...ticket, status: normalizeStatus(ticket.status) })));
    } catch (error) {
      console.error(error);
      toast.error("Unable to refresh remediation backlog");
    }
  };

  useEffect(() => {
    void fetchTickets();
  }, []);

  useEffect(() => {
    void fetchTickets(activeTab);
  }, [activeTab]);

  const counts = useMemo(
    () => ({
      ALL: tickets.length,
      OPEN: tickets.filter((ticket) => ticket.status === "OPEN").length,
      IN_PROGRESS: tickets.filter((ticket) => ticket.status === "IN_PROGRESS").length,
      DONE: tickets.filter((ticket) => ticket.status === "DONE").length,
    }),
    [tickets],
  );

  const activeTickets = useMemo(() => {
    const rows = tickets.filter((ticket) => activeTab === "ALL" || ticket.status === activeTab);
    return [...rows].sort((a, b) => {
      let comparison = 0;
      if (sortKey === "finding") {
        comparison = a.finding.localeCompare(b.finding);
      } else if (sortKey === "priority") {
        comparison = PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
      } else if (sortKey === "status") {
        comparison = STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status);
      } else {
        comparison = a.eal_impact_lakh - b.eal_impact_lakh;
      }
      return sortDir === "asc" ? comparison : -comparison;
    });
  }, [tickets, activeTab, sortKey, sortDir]);

  const resolvedTotal = useMemo(
    () =>
      selectedIds.reduce((sum, id) => {
        const ticket = tickets.find((item) => item.id === id);
        return sum + (ticket?.eal_impact_lakh ?? 0);
      }, 0),
    [selectedIds, tickets],
  );

  const handleSort = (key: typeof sortKey) => {
    if (sortKey === key) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDir("desc");
  };

  const handleChangeStatus = async (ticket: BacklogTicket, nextStatus: TicketStatus) => {
    try {
      const response = await fetch(`/api/v1/backlog/tickets/${ticket.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      if (!response.ok) {
        throw new Error("Status update failed");
      }
      const payload = (await response.json()) as { ticket?: BacklogTicket; eal_reduction_lakh?: number; message?: string };
      const updated = payload.ticket ?? { ...ticket, status: nextStatus };
      setTickets((current) => current.map((item) => (item.id === ticket.id ? { ...item, ...updated, status: normalizeStatus(updated.status) } : item)));
      if (nextStatus === "DONE") {
        toast.success(`Ticket resolved — ₹${payload.eal_reduction_lakh ?? ticket.eal_impact_lakh} Lakhs eliminated from EAL`, {
          description: ticket.finding,
        });
      } else {
        toast.success(`Status updated to ${STATUS_LABEL[nextStatus]}`, { description: ticket.finding });
      }
      if (selectedTicket?.id === ticket.id) {
        setSelectedTicket({ ...selectedTicket, status: nextStatus });
      }
    } catch (error) {
      console.error(error);
      toast.error("Unable to update ticket status");
    }
  };

  const cycleTicketStatus = (ticket: BacklogTicket) => {
    const currentIndex = STATUS_ORDER.indexOf(ticket.status);
    const nextStatus = STATUS_ORDER[(currentIndex + 1) % STATUS_ORDER.length];
    void handleChangeStatus(ticket, nextStatus);
  };

  const handleCreateTicket = async () => {
    if (!form.finding.trim()) {
      toast.error("Finding name is required");
      return;
    }

    const payload = {
      finding: form.finding.trim(),
      asset_id: form.asset_id,
      business_unit: form.business_unit.trim() || "Corporate IT",
      eal_impact_lakh: Number(form.eal_impact_lakh || ASSET_IMPACT_SUGGESTIONS[form.asset_id] || 24),
      owner: form.owner.trim() || "Unassigned",
      priority: form.priority,
      status: "OPEN",
      remediation_command: `sudo /opt/cyberisk/bin/patch-asset --asset ${form.asset_id} --owner '${form.owner.trim() || "Unassigned"}' --priority ${form.priority.toLowerCase()}`,
    };

    try {
      const response = await fetch("/api/v1/backlog/tickets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error("Ticket creation failed");
      }
      const created = (await response.json()) as BacklogTicket;
      setTickets((current) => [created, ...current]);
      setForm({
        finding: "",
        asset_id: "core-pay-db-01",
        business_unit: "Core Banking",
        eal_impact_lakh: "68",
        owner: "",
        priority: "HIGH",
      });
      setShowForm(false);
      setActiveTab("ALL");
      toast.success("Ticket created", { description: created.finding });
    } catch (error) {
      console.error(error);
      toast.error("Could not create a new ticket");
    }
  };

  const handleAssetChange = (assetId: string) => {
    const nextBusinessUnit =
      assetId === "core-pay-db-01"
        ? "Core Banking"
        : assetId === "pay-gw-03"
          ? "Payments"
          : assetId === "corp-fs-02"
            ? "Corporate IT"
            : assetId === "cards-api-legacy"
              ? "Cards & Lending"
              : assetId === "iam-sso-01"
                ? "Corporate IT"
                : assetId === "branch-pos-fleet"
                  ? "Cards & Lending"
                  : "All BUs";

    setForm((current) => ({
      ...current,
      asset_id: assetId,
      business_unit: nextBusinessUnit,
      eal_impact_lakh: String(ASSET_IMPACT_SUGGESTIONS[assetId] ?? 24),
    }));
  };

  const handleJiraSync = async (ticket: BacklogTicket) => {
    try {
      const response = await fetch(`/api/v1/backlog/tickets/${ticket.id}/jira-sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!response.ok) {
        throw new Error("Jira sync failed");
      }
      const payload = (await response.json()) as { jira_key?: string };
      setTickets((current) => current.map((item) => (item.id === ticket.id ? { ...item, jira_key: payload.jira_key ?? item.jira_key } : item)));
      setSelectedTicket((current) => (current && current.id === ticket.id ? { ...current, jira_key: payload.jira_key ?? current.jira_key } : current));
      toast.success("Jira sync created", { description: payload.jira_key ?? "New ticket exported" });
    } catch (error) {
      console.error(error);
      toast.error("Could not sync to Jira");
    }
  };

  const handleBatchResolve = async () => {
    if (selectedIds.length === 0) return;
    try {
      const response = await fetch("/api/v1/backlog/batch-resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket_ids: selectedIds }),
      });
      if (!response.ok) {
        throw new Error("Batch resolve failed");
      }
      const payload = (await response.json()) as { total_eal_reduced_lakh?: number; resolved_count?: number };
      setTickets((current) => current.map((ticket) => (selectedIds.includes(ticket.id) ? { ...ticket, status: "DONE", sla_hours_remaining: 0 } : ticket)));
      setSelectedIds([]);
      toast.success(`Ticket resolved — ₹${payload.total_eal_reduced_lakh ?? resolvedTotal} Lakhs eliminated from EAL`, {
        description: `Resolved ${payload.resolved_count ?? selectedIds.length} tickets`,
      });
      setSelectedTicket(null);
      await fetchTickets(activeTab);
    } catch (error) {
      console.error(error);
      toast.error("Could not resolve selected tickets");
    }
  };

  const SortIcon = ({ field }: { field: typeof sortKey }) =>
    sortKey === field ? (
      sortDir === "asc" ? <ChevronUp size={10} /> : <ChevronDown size={10} />
    ) : (
      <ChevronsUpDown size={10} style={{ opacity: 0.4 }} />
    );

  return (
    <section className="section-container stagger-enter stagger-1">
      <div className="section-header">
        <div>
          <span className="eyebrow eyebrow--gold">TECHNICAL DRILL-DOWN</span>
          <h1>Remediation backlog</h1>
          <p>Every ticket is linked back to the finding, its EAL contribution, and the control drift behind the exposure.</p>
        </div>
        <button className="primary-button" onClick={() => setShowForm((value) => !value)} type="button">
          {showForm ? <X size={14} /> : <Plus size={14} />} {showForm ? "Cancel" : "New ticket"}
        </button>
      </div>

      {showForm && (
        <div className="terminal-card new-ticket-form stagger-enter stagger-1">
          <h3 className="form-title">Create new finding</h3>
          <div className="form-grid">
            <label className="form-field">
              <span>Finding name *</span>
              <input value={form.finding} onChange={(event) => setForm((current) => ({ ...current, finding: event.target.value }))} className="form-input" placeholder="e.g. SQL injection on admin API" />
            </label>
            <label className="form-field">
              <span>Asset</span>
              <select value={form.asset_id} onChange={(event) => handleAssetChange(event.target.value)} className="form-input">
                {ASSET_OPTIONS.map((asset) => (
                  <option key={asset.value} value={asset.value}>{asset.label}</option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>Business Unit</span>
              <input value={form.business_unit} onChange={(event) => setForm((current) => ({ ...current, business_unit: event.target.value }))} className="form-input" placeholder="Core Banking" />
            </label>
            <label className="form-field">
              <span>EAL Impact (₹ Lakhs)</span>
              <input type="number" min="0" value={form.eal_impact_lakh} onChange={(event) => setForm((current) => ({ ...current, eal_impact_lakh: event.target.value }))} className="form-input" placeholder="68" />
            </label>
            <label className="form-field">
              <span>Owner name</span>
              <input value={form.owner} onChange={(event) => setForm((current) => ({ ...current, owner: event.target.value }))} className="form-input" placeholder="A. Kumar" />
            </label>
            <label className="form-field">
              <span>Priority</span>
              <select value={form.priority} onChange={(event) => setForm((current) => ({ ...current, priority: event.target.value as TicketPriority }))} className="form-input">
                {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as TicketPriority[]).map((priority) => (
                  <option key={priority} value={priority}>{priority}</option>
                ))}
              </select>
            </label>
          </div>
          <button className="primary-button" style={{ marginTop: 16 }} onClick={handleCreateTicket} type="button">
            Add to backlog
          </button>
        </div>
      )}

      <div className="tab-group">
        {(["ALL", "OPEN", "IN_PROGRESS", "DONE"] as StatusTab[]).map((tab) => (
          <button key={tab} type="button" className={`tab ${activeTab === tab ? "is-active" : ""}`} onClick={() => setActiveTab(tab)}>
            {tab === "ALL" ? "All" : tab === "OPEN" ? "Open" : tab === "IN_PROGRESS" ? "In progress" : "Done"} ({counts[tab] ?? 0})
          </button>
        ))}
      </div>

      <div className="terminal-card table-card">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 44 }}>
                <input
                  type="checkbox"
                  aria-label="Select all"
                  checked={activeTickets.length > 0 && activeTickets.every((ticket) => selectedIds.includes(ticket.id))}
                  onChange={(event) => {
                    const ids = activeTickets.map((ticket) => ticket.id);
                    const mergedIds = event.target.checked
                      ? [...selectedIds.filter((id) => !ids.includes(id)), ...ids]
                      : selectedIds.filter((id) => !ids.includes(id));
                    setSelectedIds(mergedIds);
                  }}
                />
              </th>
              <th style={{ cursor: "pointer" }} onClick={() => handleSort("finding")}>
                <span className="th-sort">Finding <SortIcon field="finding" /></span>
              </th>
              <th>Asset / BU</th>
              <th style={{ cursor: "pointer" }} onClick={() => handleSort("eal_impact_lakh")}>
                <span className="th-sort">EAL impact <SortIcon field="eal_impact_lakh" /></span>
              </th>
              <th>SLA</th>
              <th>Owner</th>
              <th style={{ cursor: "pointer" }} onClick={() => handleSort("priority")}>
                <span className="th-sort">Priority <SortIcon field="priority" /></span>
              </th>
              <th style={{ cursor: "pointer" }} onClick={() => handleSort("status")}>
                <span className="th-sort">Status <SortIcon field="status" /></span>
              </th>
            </tr>
          </thead>
          <tbody>
            {activeTickets.length === 0 ? (
              <tr>
                <td colSpan={8} className="empty-row">No findings in this category.</td>
              </tr>
            ) : (
              activeTickets.map((ticket) => {
                const isSelected = selectedIds.includes(ticket.id);
                const sla = describeSla(ticket.sla_hours_remaining);
                return (
                  <tr key={ticket.id} className={selectedTicket?.id === ticket.id ? "row-selected" : ""} onClick={() => setSelectedTicket(ticket)}>
                    <td onClick={(event) => event.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(event) => {
                          setSelectedIds((current) =>
                            event.target.checked ? (current.includes(ticket.id) ? current : [...current, ticket.id]) : current.filter((id) => id !== ticket.id),
                          );
                        }}
                      />
                    </td>
                    <td className="font-medium text-light">
                      <div className="cell-stack">
                        <span>{ticket.finding}</span>
                        {ticket.jira_key && <small className="jira-pill">{ticket.jira_key}</small>}
                      </div>
                    </td>
                    <td>
                      <div className="cell-stack small-stack">
                        <span className="text-light">{ticket.asset_id}</span>
                        <span className="text-muted">{ticket.business_unit}</span>
                      </div>
                    </td>
                    <td className="text-red font-medium">{fmtImpact(ticket.eal_impact_lakh)}</td>
                    <td>
                      <span className={sla.className}>{sla.label}</span>
                    </td>
                    <td>
                      <div className="owner-cell">
                        <span className="avatar-micro">{ticket.owner.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase()}</span>
                        <span className="text-light">{ticket.owner}</span>
                      </div>
                    </td>
                    <td>
                      <div className="priority-cell">
                        <span className="priority-dot" style={{ background: priorityColor[ticket.priority] }} />
                        <span className="text-light">{ticket.priority}</span>
                      </div>
                    </td>
                    <td>
                      <button
                        type="button"
                        className={`status-badge status-badge--${ticket.status.toLowerCase().replace("_", "-")}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          cycleTicketStatus(ticket);
                        }}
                      >
                        {STATUS_LABEL[ticket.status]}
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {selectedTicket && (
        <div className="compliance-drawer-backdrop" onClick={() => setSelectedTicket(null)}>
          <aside className="compliance-drawer remediation-drawer" onClick={(event) => event.stopPropagation()}>
            <div className="compliance-drawer-header">
              <div>
                <span className="decision-kicker">Ticket detail</span>
                <h3>{selectedTicket.finding}</h3>
              </div>
              <button className="close-button" onClick={() => setSelectedTicket(null)} type="button">×</button>
            </div>

            <div className="drawer-grid">
              <div className="drawer-block">
                <h4>Remediation command</h4>
                <pre className="command-box">{selectedTicket.remediation_command}</pre>
                <div className="drawer-actions split-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => {
                      void navigator.clipboard
                        ?.writeText(selectedTicket.remediation_command)
                        .then(() => toast.success("Command copied"))
                        .catch(() => toast.error("Copy failed"));
                    }}
                  >
                    <Copy size={14} /> Copy
                  </button>
                  <button className="primary-button" type="button" onClick={() => void handleJiraSync(selectedTicket)}>
                    <Download size={14} /> Sync to Jira
                  </button>
                </div>
              </div>
              <div className="drawer-block">
                <h4>Exposure summary</h4>
                <ul className="detail-list">
                  <li><strong>Asset:</strong> {selectedTicket.asset_id}</li>
                  <li><strong>Business unit:</strong> {selectedTicket.business_unit}</li>
                  <li><strong>EAL impact:</strong> {fmtImpact(selectedTicket.eal_impact_lakh)}</li>
                  <li><strong>Owner:</strong> {selectedTicket.owner}</li>
                  <li><strong>Priority:</strong> {selectedTicket.priority}</li>
                  <li><strong>SLA:</strong> {selectedTicket.sla_hours_remaining}h remaining</li>
                </ul>
              </div>
            </div>

            <div className="drawer-block">
              <h4>Lifecycle actions</h4>
              <div className="inline-status-row">
                {STATUS_ORDER.map((status) => (
                  <button
                    key={status}
                    type="button"
                    className={`mini-status ${selectedTicket.status === status ? "mini-status--active" : ""}`}
                    onClick={() => void handleChangeStatus(selectedTicket, status)}
                  >
                    {STATUS_LABEL[status]}
                  </button>
                ))}
              </div>
            </div>
          </aside>
        </div>
      )}

      {selectedIds.length > 0 && (
        <div className="batch-action-bar">
          <span>Resolve Selected ({selectedIds.length}) &amp; Reclaim ₹{resolvedTotal.toFixed(0)} Lakhs</span>
          <button type="button" className="primary-button" onClick={() => void handleBatchResolve()}>
            <Check size={14} /> Resolve selected
          </button>
        </div>
      )}
    </section>
  );
}
