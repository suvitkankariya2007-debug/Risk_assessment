import { useState, useRef, useEffect } from "react";
import { Send, Sparkles, Bot } from "lucide-react";

type Role = "user" | "copilot";

interface Message {
  id: number;
  role: Role;
  text: string;
  citation?: string;
  timestamp: Date;
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: 1,
    role: "copilot",
    text: "Hello! I'm CyberRiskIQ Copilot. I can answer questions about your organisation's risk exposure, control effectiveness, compliance gaps, and remediation priorities. Every answer I give cites the underlying EAL figure or source — never a bare claim.",
    citation: "Model grounding: live EAL tables · ISO/NIST/RBI clause store",
    timestamp: new Date(Date.now() - 120000),
  },
];

const CANNED_RESPONSES: Record<string, { text: string; citation: string }> = {
  mfa: {
    text: "Enforcing MFA on all privileged and remote-access accounts reduces org-wide EAL by an estimated ₹68L/yr (14%), primarily by cutting credential-theft loss-event frequency on Payments and Corporate IT. Estimated rollout cost is ₹12L, giving a ROSI of 467% — one of the highest-yield controls available this cycle.",
    citation: "Scenario simulator · run #A114 · Control: Enforce MFA on all privileged accounts",
  },
  vuln: {
    text: "Three findings account for 41% of total EAL: an unpatched Apache Struts RCE on the payments gateway (₹61L), an over-permissioned IAM role on the core banking cluster (₹48L), and unencrypted backups in the corporate file share (₹22L). Full ranked list is in the Risk Quantification view.",
    citation: "Risk register · top-3 by EAL contribution · last recomputed 4 min ago",
  },
  rosi: {
    text: "Top ROSI controls this cycle: MFA rollout (467%), critical-CVE patch SLA (312%), EDR coverage to 100% (204%). The investment optimizer module can bundle these into a single spend recommendation under your budget constraint.",
    citation: "Investment Optimizer · knapsack solve #K-09 · ₹34L budget",
  },
  compliance: {
    text: "Your weakest framework is RBI CSF at 69% — driven mainly by the network segmentation gap (Clause 5.4) and incomplete access-logging on the payments switch. Fixing these two controls would raise RBI CSF coverage to approximately 84% and close 4 open findings.",
    citation: "Compliance Mapping · RBI CSF gap analysis · 4 open clauses",
  },
  eal: {
    text: "Current org-wide Expected Annual Loss is ₹4.82 Cr (95th-percentile VaR: ₹9.15 Cr). Core Banking DB Cluster is the largest single contributor at ₹1.12 Cr. The 12-month trend shows a 14% reduction from ₹5.61 Cr — driven by the IAM consolidation project completed in Q2.",
    citation: "Executive Overview · Monte Carlo engine · 18,421 evidence points",
  },
  default: {
    text: "Based on the current risk ledger, I can see that query relates to your exposure model. The Monte Carlo engine last ran 4 minutes ago across 86 assets and 4 business units. For a precise answer, try asking about a specific asset, business unit, control, or framework — or use one of the suggestion chips below.",
    citation: "Risk ledger · last sync 4 min ago",
  },
};

function pickResponse(input: string): { text: string; citation: string } {
  const q = input.toLowerCase();
  if (q.includes("mfa") || q.includes("multi-factor") || q.includes("authentication")) return CANNED_RESPONSES.mfa;
  if (q.includes("vuln") || q.includes("loss") || q.includes("drive") || q.includes("contribut")) return CANNED_RESPONSES.vuln;
  if (q.includes("rosi") || q.includes("return") || q.includes("invest") || q.includes("q2") || q.includes("q3")) return CANNED_RESPONSES.rosi;
  if (q.includes("compliance") || q.includes("framework") || q.includes("rbi") || q.includes("iso") || q.includes("nist")) return CANNED_RESPONSES.compliance;
  if (q.includes("eal") || q.includes("exposure") || q.includes("annual loss") || q.includes("var")) return CANNED_RESPONSES.eal;
  if (q.includes("business unit") || q.includes("highest risk")) return CANNED_RESPONSES.vuln;
  return CANNED_RESPONSES.default;
}

const CHIPS = [
  "Highest risk by business unit",
  "Show ROSI for MFA rollout",
  "Compare Q2 vs Q3 exposure",
  "What compliance gaps remain?",
  "Current EAL breakdown",
];

let nextId = 10;

export default function AICopilot() {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const send = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isTyping) return;

    const userMsg: Message = {
      id: nextId++,
      role: "user",
      text: trimmed,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    const delay = 1200 + Math.random() * 800;
    setTimeout(() => {
      const response = pickResponse(trimmed);
      const botMsg: Message = {
        id: nextId++,
        role: "copilot",
        text: response.text,
        citation: response.citation,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMsg]);
      setIsTyping(false);
    }, delay);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    send(input);
  };

  const handleChip = (chip: string) => {
    setInput(chip);
    send(chip);
    inputRef.current?.focus();
  };

  const fmt = (d: Date) =>
    d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true });

  return (
    <section className="section-container stagger-enter stagger-1">
      <div className="section-header">
        <div>
          <span className="eyebrow eyebrow--gold">AI DECISION-SUPPORT LAYER</span>
          <h1>Ask the risk ledger a question</h1>
          <p>RAG over live risk tables and framework documents. Every answer cites the underlying EAL figure, never a bare claim.</p>
        </div>
        <div className="copilot-status-badge">
          <span className="footer-live" style={{ width: 7, height: 7, flexShrink: 0 }} />
          <span style={{ fontSize: 9, color: "var(--green)", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Model active
          </span>
        </div>
      </div>

      <div className="copilot-grid">
        {/* Chat area */}
        <div className="chat-interface stagger-enter stagger-2">
          <div className="chat-history">
            {messages.map((msg) => (
              <div key={msg.id} className={`message ${msg.role === "user" ? "user-message" : "copilot-message"}`}>
                <div className="message-sender">
                  {msg.role === "user" ? "YOU" : (
                    <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                      <Bot size={10} /> CyberRiskIQ Copilot
                    </span>
                  )}
                  <span className="message-time">{fmt(msg.timestamp)}</span>
                </div>
                <div className="message-bubble">
                  <p style={{ margin: 0 }}>{msg.text}</p>
                  {msg.citation && (
                    <div className="message-action">
                      <span className="text-gold" style={{ display: "flex", alignItems: "center", gap: 5 }}>
                        <Sparkles size={10} /> {msg.citation}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="message copilot-message">
                <div className="message-sender">
                  <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                    <Bot size={10} /> CyberRiskIQ Copilot
                  </span>
                </div>
                <div className="message-bubble">
                  <div className="typing-indicator">
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form className="chat-input-area" onSubmit={handleSubmit}>
            <div className="input-wrapper">
              <input
                ref={inputRef}
                type="text"
                placeholder="Ask about exposure, a control, or a business unit..."
                className="chat-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isTyping}
              />
              <button
                className="primary-button ask-button"
                type="submit"
                disabled={!input.trim() || isTyping}
              >
                <Send size={13} /> Ask
              </button>
            </div>
            <div className="suggestion-chips">
              {CHIPS.map((chip) => (
                <button
                  key={chip}
                  type="button"
                  className="chip"
                  onClick={() => handleChip(chip)}
                  disabled={isTyping}
                >
                  {chip}
                </button>
              ))}
            </div>
          </form>
        </div>

        {/* Sidebar */}
        <div className="copilot-sidebar">
          <div className="terminal-card sidebar-card stagger-enter stagger-3">
            <h3>Model grounding</h3>
            <span className="eyebrow">WHAT THE COPILOT READS</span>
            <ul className="grounding-list">
              <li><span>→</span> Live EAL / VaR tables (asset, BU, org)</li>
              <li><span>→</span> Control effectiveness &amp; ROSI store</li>
              <li><span>→</span> ISO / NIST / CIS / RBI / SEBI clause text</li>
              <li><span>→</span> Scenario simulator run history</li>
            </ul>
          </div>

          <div className="terminal-card sidebar-card stagger-enter stagger-4">
            <h3>Conversation</h3>
            <span className="eyebrow">THIS SESSION</span>
            <div className="session-stats">
              <div className="session-stat">
                <strong>{messages.filter(m => m.role === "user").length}</strong>
                <span>questions asked</span>
              </div>
              <div className="session-stat">
                <strong>{messages.filter(m => m.role === "copilot").length}</strong>
                <span>answers with citations</span>
              </div>
            </div>
          </div>

          <div className="terminal-card sidebar-card stagger-enter stagger-4">
            <h3>Guardrails</h3>
            <span className="eyebrow">EXPLAINABLE BY DESIGN</span>
            <p className="guardrail-text">
              Every answer must cite a source table or scenario run. The copilot recommends — it never triggers a change autonomously.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
