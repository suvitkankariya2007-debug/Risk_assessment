import { useState, useRef, useEffect } from "react";
import { Send, Sparkles, Bot } from "lucide-react";

type Role = "user" | "copilot";

type Persona = "Executive" | "CISO" | "Analyst";

interface Message {
  id: number;
  role: Role;
  text: string;
  citation?: string;
  timestamp: Date;
}

interface VerifiedMetrics {
  [key: string]: number | string;
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
  const [persona, setPersona] = useState<Persona>("Executive");
  const [verifiedMetrics, setVerifiedMetrics] = useState<VerifiedMetrics>({});
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const send = async (text: string) => {
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

    try {
      const response = await fetch("/api/v1/chat/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed, persona }),
      });

      if (!response.ok) {
        throw new Error("Copilot request failed");
      }

      const data = await response.json();
      const botMsg: Message = {
        id: nextId++,
        role: "copilot",
        text: data.reply,
        citation: (data.cited_sources || []).join(" · "),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMsg]);
      setVerifiedMetrics(data.verified_metrics || {});
    } catch (error) {
      console.error(error);
      const fallback: Message = {
        id: nextId++,
        role: "copilot",
        text: "The copilot service is unavailable right now. Please try again in a moment.",
        citation: "Backend unavailable",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, fallback]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
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
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {(["Executive", "CISO", "Analyst"] as Persona[]).map((item) => (
            <button
              key={item}
              type="button"
              className={`chip ${persona === item ? "active" : ""}`}
              onClick={() => setPersona(item)}
              style={{ padding: "7px 10px" }}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="copilot-grid">
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
              <button className="primary-button ask-button" type="submit" disabled={!input.trim() || isTyping}>
                <Send size={13} /> Ask
              </button>
            </div>
            <div className="suggestion-chips">
              {CHIPS.map((chip) => (
                <button key={chip} type="button" className="chip" onClick={() => handleChip(chip)} disabled={isTyping}>
                  {chip}
                </button>
              ))}
            </div>
          </form>
        </div>

        <div className="copilot-sidebar">
          <div className="terminal-card sidebar-card stagger-enter stagger-3">
            <h3>Verified metrics</h3>
            <span className="eyebrow">NUMBERS FROM API</span>
            <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
              {Object.entries(verifiedMetrics).length === 0 ? (
                <span style={{ color: "#a7b2bf" }}>No metrics yet.</span>
              ) : (
                Object.entries(verifiedMetrics).map(([key, value]) => (
                  <div key={key} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                    <span style={{ color: "#a7b2bf", textTransform: "capitalize" }}>{key.replace(/_/g, " ")}</span>
                    <strong style={{ color: "#eaf0f7" }}>{String(value)}</strong>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="terminal-card sidebar-card stagger-enter stagger-4">
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
                <strong>{messages.filter((message) => message.role === "user").length}</strong>
                <span>questions asked</span>
              </div>
              <div className="session-stat">
                <strong>{messages.filter((message) => message.role === "copilot").length}</strong>
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
