import { useState, useMemo } from "react";
import { Plus, X, ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";
import { toast } from "sonner";

type Priority = "Critical" | "High" | "Medium" | "Low";
type Status = "Open" | "In progress" | "Done";

interface Finding {
  id: number;
  name: string;
  asset: string;
  bu: string;
  impact: number; // in Lakhs
  ownerName: string;
  ownerInitials: string;
  priority: Priority;
  status: Status;
}

const STATUS_CYCLE: Status[] = ["Open", "In progress", "Done"];
const PRIORITY_ORDER: Record<Priority, number> = { Critical: 0, High: 1, Medium: 2, Low: 3 };

const INITIAL_FINDINGS: Finding[] = [
  { id: 1, name: "Apache Struts RCE — CVE-2025-31337",         asset: "pay-gw-03",         bu: "Payments",       impact: 61, ownerName: "R. Khanna",     ownerInitials: "RK", priority: "Critical", status: "Open" },
  { id: 2, name: "Over-permissioned IAM role — core-banking-admin", asset: "core-pay-db-01", bu: "Core Banking",   impact: 48, ownerName: "S. Patil",      ownerInitials: "SP", priority: "Critical", status: "In progress" },
  { id: 3, name: "Unencrypted backups — corporate file share", asset: "corp-fs-02",        bu: "Corporate IT",   impact: 22, ownerName: "M. Verma",      ownerInitials: "MV", priority: "High",     status: "In progress" },
  { id: 4, name: "MFA gap on 340 privileged accounts",         asset: "org-wide",          bu: "All BUs",        impact: 68, ownerName: "A. Chatterjee", ownerInitials: "AC", priority: "High",     status: "Open" },
  { id: 5, name: "EDR agent missing on 18% of endpoints",     asset: "fleet",             bu: "Corporate IT",   impact: 14, ownerName: "R. Khanna",     ownerInitials: "RK", priority: "Medium",   status: "Open" },
  { id: 6, name: "TLS 1.0 still enabled — legacy cards API",  asset: "cards-api-legacy",  bu: "Cards & Lending", impact: 6, ownerName: "S. Patil",      ownerInitials: "SP", priority: "Low",      status: "Done" },
];

type SortKey = "name" | "impact" | "priority" | "status";
type SortDir = "asc" | "desc";

const fmtImpact = (l: number) => l >= 100 ? `₹${(l / 100).toFixed(2)}Cr` : `₹${l}L`;

const priorityColor: Record<Priority, string> = {
  Critical: "#ef858d", High: "var(--gold)", Medium: "#f2c86f", Low: "#51d1a1",
};

export default function RemediationBacklog() {
  const [findings, setFindings] = useState<Finding[]>(INITIAL_FINDINGS);
  const [activeTab, setActiveTab] = useState<"All" | Status>("All");
  const [sortKey, setSortKey] = useState<SortKey>("impact");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", asset: "", bu: "", impact: "", ownerName: "", priority: "High" as Priority });

  const counts = useMemo(() => ({
    All: findings.length,
    Open: findings.filter(f => f.status === "Open").length,
    "In progress": findings.filter(f => f.status === "In progress").length,
    Done: findings.filter(f => f.status === "Done").length,
  }), [findings]);

  const displayed = useMemo(() => {
    let rows = activeTab === "All" ? findings : findings.filter(f => f.status === activeTab);
    rows = [...rows].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "impact") cmp = a.impact - b.impact;
      else if (sortKey === "priority") cmp = PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
      else if (sortKey === "name") cmp = a.name.localeCompare(b.name);
      else if (sortKey === "status") cmp = a.status.localeCompare(b.status);
      return sortDir === "asc" ? cmp : -cmp;
    });
    return rows;
  }, [findings, activeTab, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  const cycleStatus = (id: number) => {
    setFindings(prev => prev.map(f => {
      if (f.id !== id) return f;
      const idx = STATUS_CYCLE.indexOf(f.status);
      const next = STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length];
      toast(`Status updated → ${next}`, { description: f.name });
      return { ...f, status: next };
    }));
  };

  const addFinding = () => {
    if (!form.name.trim()) { toast.error("Finding name is required"); return; }
    const initials = form.ownerName.trim()
      ? form.ownerName.trim().split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2)
      : "??";
    const newItem: Finding = {
      id: Date.now(),
      name: form.name.trim(),
      asset: form.asset.trim() || "unknown",
      bu: form.bu.trim() || "Unknown",
      impact: parseFloat(form.impact) || 0,
      ownerName: form.ownerName.trim() || "Unassigned",
      ownerInitials: initials,
      priority: form.priority,
      status: "Open",
    };
    setFindings(prev => [newItem, ...prev]);
    setForm({ name: "", asset: "", bu: "", impact: "", ownerName: "", priority: "High" });
    setShowForm(false);
    toast.success("Ticket created", { description: newItem.name });
  };

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k ? (sortDir === "asc" ? <ChevronUp size={10} /> : <ChevronDown size={10} />) : <ChevronsUpDown size={10} style={{ opacity: 0.4 }} />;

  const tabs: Array<"All" | Status> = ["All", "Open", "In progress", "Done"];

  return (
    <section className="section-container stagger-enter stagger-1">
      <div className="section-header">
        <div>
          <span className="eyebrow eyebrow--gold">TECHNICAL DRILL-DOWN</span>
          <h1>Remediation backlog</h1>
          <p>Every ticket is linked back to the finding, its EAL contribution, and the framework clause it closes.</p>
        </div>
        <button className="primary-button" onClick={() => setShowForm(s => !s)}>
          {showForm ? <X size={14} /> : <Plus size={14} />} {showForm ? "Cancel" : "New ticket"}
        </button>
      </div>

      {/* Inline new ticket form */}
      {showForm && (
        <div className="terminal-card new-ticket-form stagger-enter stagger-1">
          <h3 style={{ margin: "0 0 16px", fontSize: 13, color: "#e5ebf1" }}>Create new finding</h3>
          <div className="form-grid">
            <div className="form-field">
              <label>Finding name *</label>
              <input className="form-input" placeholder="e.g. SQL injection on admin API" value={form.name}
                onChange={e => setForm(p => ({ ...p, name: e.target.value }))} />
            </div>
            <div className="form-field">
              <label>Asset</label>
              <input className="form-input" placeholder="e.g. admin-api-01" value={form.asset}
                onChange={e => setForm(p => ({ ...p, asset: e.target.value }))} />
            </div>
            <div className="form-field">
              <label>Business Unit</label>
              <input className="form-input" placeholder="e.g. Core Banking" value={form.bu}
                onChange={e => setForm(p => ({ ...p, bu: e.target.value }))} />
            </div>
            <div className="form-field">
              <label>EAL Impact (₹ Lakhs)</label>
              <input className="form-input" type="number" min="0" placeholder="e.g. 25" value={form.impact}
                onChange={e => setForm(p => ({ ...p, impact: e.target.value }))} />
            </div>
            <div className="form-field">
              <label>Owner name</label>
              <input className="form-input" placeholder="e.g. A. Kumar" value={form.ownerName}
                onChange={e => setForm(p => ({ ...p, ownerName: e.target.value }))} />
            </div>
            <div className="form-field">
              <label>Priority</label>
              <select className="form-input" value={form.priority}
                onChange={e => setForm(p => ({ ...p, priority: e.target.value as Priority }))}>
                {(["Critical", "High", "Medium", "Low"] as Priority[]).map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
          </div>
          <button className="primary-button" style={{ marginTop: 16 }} onClick={addFinding}>Add to backlog</button>
        </div>
      )}

      {/* Tabs */}
      <div className="tab-group">
        {tabs.map(tab => (
          <button
            key={tab}
            className={`tab ${activeTab === tab ? "is-active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab} ({counts[tab]})
          </button>
        ))}
      </div>

      <div className="terminal-card table-card">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ cursor: "pointer" }} onClick={() => handleSort("name")}>
                <span className="th-sort">FINDING <SortIcon k="name" /></span>
              </th>
              <th>ASSET / BU</th>
              <th style={{ cursor: "pointer" }} onClick={() => handleSort("impact")}>
                <span className="th-sort">EAL IMPACT <SortIcon k="impact" /></span>
              </th>
              <th>OWNER</th>
              <th style={{ cursor: "pointer" }} onClick={() => handleSort("priority")}>
                <span className="th-sort">PRIORITY <SortIcon k="priority" /></span>
              </th>
              <th style={{ cursor: "pointer" }} onClick={() => handleSort("status")}>
                <span className="th-sort">STATUS <SortIcon k="status" /></span>
              </th>
            </tr>
          </thead>
          <tbody>
            {displayed.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: "32px 0", color: "#687483" }}>
                  No findings in this category.
                </td>
              </tr>
            ) : displayed.map((item) => (
              <tr key={item.id}>
                <td className="font-medium text-light">{item.name}</td>
                <td>
                  <span className="text-light">{item.asset}</span>{" "}
                  <span className="text-muted">· {item.bu}</span>
                </td>
                <td className="text-red font-medium">{fmtImpact(item.impact)}</td>
                <td>
                  <div className="owner-cell">
                    <span className="avatar-micro">{item.ownerInitials}</span>
                    <span className="text-light">{item.ownerName}</span>
                  </div>
                </td>
                <td>
                  <div className="priority-cell">
                    <span className="priority-dot" style={{ background: priorityColor[item.priority] }} />
                    <span className="text-light">{item.priority}</span>
                  </div>
                </td>
                <td>
                  <button
                    className={`status-badge status-badge--${item.status.toLowerCase().replace(" ", "-")}`}
                    onClick={() => cycleStatus(item.id)}
                    title="Click to advance status"
                    style={{ cursor: "pointer" }}
                  >
                    {item.status}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
