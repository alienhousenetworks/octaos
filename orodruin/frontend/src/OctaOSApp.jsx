import { useEffect, useState } from "react";
import {
  Activity,
  Bot,
  Briefcase,
  Globe,
  LayoutDashboard,
  LogOut,
  Sparkles,
  Target,
} from "lucide-react";
import { apiFetch, getToken, setToken } from "./api.js";
import OrodruinLegacyApp from "./App.jsx";
import "./octaos.css";

const NAV_ITEMS = [
  { id: "overview", label: "Executive Dashboard", icon: LayoutDashboard },
  { id: "intelligence", label: "Company & Lead Intel", icon: Target },
  { id: "globe", label: "Global OSINT Map", icon: Globe },
  { id: "business", label: "CRM & Content Studio", icon: Briefcase },
  { id: "agents", label: "AI Operations", icon: Bot },
  { id: "learning", label: "Learning Center", icon: Activity },
];

export default function OctaOSApp() {
  const [token, setTok] = useState(getToken());
  const [user, setUser] = useState(null);
  const [tab, setTab] = useState("overview");
  const [error, setError] = useState("");

  // Auth form state
  const [authMode, setAuthMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [subdomain, setSubdomain] = useState("");

  // Live platform state
  const [companies, setCompanies] = useState([]);
  const [leads, setLeads] = useState([]);
  const [deals, setDeals] = useState([]);
  const [assets, setAssets] = useState([]);
  const [learning, setLearning] = useState(null);
  const [strategies, setStrategies] = useState([]);
  const [aiConfig, setAiConfig] = useState(null);

  // Interactive forms
  const [compName, setCompName] = useState("");
  const [compIndustry, setCompIndustry] = useState("");
  const [leadTopic, setLeadTopic] = useState("");
  const [orchGoal, setOrchGoal] = useState("");
  const [orchResult, setOrchResult] = useState(null);
  const [contentType, setContentType] = useState("image");
  const [contentPrompt, setContentPrompt] = useState("");

  async function refreshAll() {
    try {
      const [me, c, l, d, a, lr, st, cfg] = await Promise.all([
        apiFetch("/api/v1/auth/me"),
        apiFetch("/api/v1/intelligence/companies"),
        apiFetch("/api/v1/intelligence/leads"),
        apiFetch("/api/v1/business/deals"),
        apiFetch("/api/v1/business/content"),
        apiFetch("/api/v1/learning/summary"),
        apiFetch("/api/v1/learning/strategies"),
        apiFetch("/api/v1/agents/ai-config"),
      ]);
      setUser(me);
      setCompanies(c);
      setLeads(l);
      setDeals(d);
      setAssets(a);
      setLearning(lr);
      setStrategies(st);
      setAiConfig(cfg);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (token) refreshAll();
  }, [token]);

  async function handleAuth(e) {
    e.preventDefault();
    setError("");
    try {
      const path = authMode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register";
      const body =
        authMode === "login"
          ? { email, password, subdomain: subdomain || undefined }
          : { tenant_name: tenantName, subdomain, email, password };
      const res = await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
      setToken(res.access_token);
      setTok(res.access_token);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleResearchCompany(e) {
    e.preventDefault();
    if (!compName.trim()) return;
    await apiFetch("/api/v1/intelligence/companies/research", {
      method: "POST",
      body: JSON.stringify({ name: compName, industry: compIndustry || undefined }),
    });
    setCompName("");
    setCompIndustry("");
    refreshAll();
  }

  async function handleDiscoverLeads(e) {
    e.preventDefault();
    if (!leadTopic.trim()) return;
    await apiFetch("/api/v1/intelligence/leads/discover", {
      method: "POST",
      body: JSON.stringify({ topic: leadTopic, count: 3 }),
    });
    setLeadTopic("");
    refreshAll();
  }

  async function handleExecuteAgent(e) {
    e.preventDefault();
    if (!orchGoal.trim()) return;
    const res = await apiFetch("/api/v1/agents/execute", {
      method: "POST",
      body: JSON.stringify({ goal: orchGoal, topic: orchGoal }),
    });
    setOrchResult(res);
    setOrchGoal("");
    refreshAll();
  }

  async function handleGenerateContent(e) {
    e.preventDefault();
    if (!contentPrompt.trim()) return;
    await apiFetch("/api/v1/business/content/generate", {
      method: "POST",
      body: JSON.stringify({ asset_type: contentType, prompt: contentPrompt }),
    });
    setContentPrompt("");
    refreshAll();
  }

  if (!token) {
    return (
      <div className="octa-auth-wrap">
        <form className="octa-auth-box" onSubmit={handleAuth}>
          <div style={{ fontSize: 20, fontWeight: 700, color: "var(--accent)" }}>OCTAOS</div>
          <div style={{ fontSize: 12, color: "var(--muted)" }}>
            Unified Business Intelligence & Automation OS
          </div>
          {authMode === "register" && (
            <>
              <input
                className="octa-input"
                placeholder="Company / Tenant Name"
                value={tenantName}
                onChange={(e) => setTenantName(e.target.value)}
                required
              />
              <input
                className="octa-input"
                placeholder="Subdomain (e.g. acme)"
                value={subdomain}
                onChange={(e) => setSubdomain(e.target.value)}
                required
              />
            </>
          )}
          <input
            className="octa-input"
            type="email"
            placeholder="Work Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="octa-input"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <div style={{ color: "var(--danger)", fontSize: 12 }}>{error}</div>}
          <button className="octa-btn" type="submit">
            {authMode === "login" ? "Sign In" : "Create Workspace"}
          </button>
          <button
            type="button"
            className="octa-btn secondary"
            onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}
          >
            {authMode === "login" ? "Need a workspace? Register" : "Already have an account? Sign In"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="octa-shell">
      <aside className="octa-sidebar">
        <div className="octa-brand">OCTAOS · OSINT</div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`octa-nav-btn ${tab === item.id ? "active" : ""}`}
              onClick={() => setTab(item.id)}
            >
              <Icon size={16} />
              <span>{item.label}</span>
            </button>
          );
        })}
        <div style={{ marginTop: "auto", borderTop: "1px solid var(--border)", paddingTop: 10 }}>
          <button
            className="octa-nav-btn"
            onClick={() => {
              setToken("");
              setTok("");
            }}
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      <div className="octa-main">
        <header className="octa-topbar">
          <div>
            <strong>{NAV_ITEMS.find((n) => n.id === tab)?.label}</strong>
            {error && <span style={{ color: "var(--danger)", marginLeft: 12 }}>{error}</span>}
          </div>
          <div style={{ color: "var(--muted)" }}>
            {user ? `${user.email} (${user.role})` : "Loading..."}
          </div>
        </header>

        <main className="octa-content" style={tab === "globe" ? { padding: 0 } : undefined}>
          {tab === "overview" && (
            <>
              <div className="octa-grid">
                <div className="octa-card">
                  <h3>Company Profiles</h3>
                  <div className="octa-metric">{companies.length}</div>
                </div>
                <div className="octa-card">
                  <h3>Qualified Leads</h3>
                  <div className="octa-metric">{leads.length}</div>
                </div>
                <div className="octa-card">
                  <h3>Active Deals</h3>
                  <div className="octa-metric">{deals.length}</div>
                </div>
                <div className="octa-card">
                  <h3>Agent Success Rate</h3>
                  <div className="octa-metric">
                    {learning ? `${Math.round(learning.overall_success_rate * 100)}%` : "0%"}
                  </div>
                </div>
              </div>
              <div className="octa-card">
                <h3>Local-First AI Runtime (Fixed Configuration)</h3>
                {aiConfig ? (
                  <div className="octa-row" style={{ marginTop: 8 }}>
                    <span className="octa-badge">Text: {aiConfig.text_model}</span>
                    <span className="octa-badge">Vision: {aiConfig.vision_model}</span>
                    <span className="octa-badge">Image: {aiConfig.image_model}</span>
                    <span className="octa-badge">Video: {aiConfig.video_model}</span>
                  </div>
                ) : (
                  <div style={{ color: "var(--muted)" }}>Loading runtime summary...</div>
                )}
              </div>
            </>
          )}

          {tab === "intelligence" && (
            <>
              <div className="octa-card" style={{ marginBottom: 16 }}>
                <h3>Research Company & Discover Leads</h3>
                <form className="octa-row" onSubmit={handleResearchCompany}>
                  <input
                    className="octa-input"
                    placeholder="Company name"
                    value={compName}
                    onChange={(e) => setCompName(e.target.value)}
                  />
                  <input
                    className="octa-input"
                    placeholder="Industry"
                    value={compIndustry}
                    onChange={(e) => setCompIndustry(e.target.value)}
                  />
                  <button className="octa-btn" type="submit">Research Company</button>
                </form>
                <form className="octa-row" onSubmit={handleDiscoverLeads}>
                  <input
                    className="octa-input"
                    placeholder="Market topic / signal (e.g. cloud security)"
                    value={leadTopic}
                    onChange={(e) => setLeadTopic(e.target.value)}
                  />
                  <button className="octa-btn" type="submit">Discover Leads</button>
                </form>
              </div>
              <div className="octa-card">
                <h3>Discovered Leads (Evidence-Backed)</h3>
                <table className="octa-table">
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Role</th>
                      <th>Opportunity</th>
                      <th>Priority</th>
                      <th>Verified Contact</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map((l) => (
                      <tr key={l.id}>
                        <td>{l.company_name}</td>
                        <td>{l.contact_role || "—"}</td>
                        <td>{l.opportunity}</td>
                        <td><span className="octa-badge">{l.priority}</span></td>
                        <td>{l.contact_verified ? "Verified" : "Pending connector"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {tab === "globe" && (
            <div style={{ height: "100%", position: "relative" }}>
              <OrodruinLegacyApp />
            </div>
          )}

          {tab === "business" && (
            <>
              <div className="octa-card" style={{ marginBottom: 16 }}>
                <h3>Content Studio (Text / Image / Video)</h3>
                <form className="octa-row" onSubmit={handleGenerateContent}>
                  <select
                    className="octa-select"
                    value={contentType}
                    onChange={(e) => setContentType(e.target.value)}
                  >
                    <option value="text">Text Copy</option>
                    <option value="image">Image Creative</option>
                    <option value="video">Video Clip</option>
                  </select>
                  <input
                    className="octa-input"
                    style={{ flex: 1 }}
                    placeholder="Describe campaign creative prompt..."
                    value={contentPrompt}
                    onChange={(e) => setContentPrompt(e.target.value)}
                  />
                  <button className="octa-btn" type="submit">Generate Asset</button>
                </form>
              </div>
              <div className="octa-card">
                <h3>Generated Assets</h3>
                <table className="octa-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Model</th>
                      <th>Prompt</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assets.map((a) => (
                      <tr key={a.id}>
                        <td>{a.asset_type}</td>
                        <td>{a.model_used}</td>
                        <td>{a.prompt}</td>
                        <td><span className="octa-badge">{a.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {tab === "agents" && (
            <div className="octa-card">
              <h3>Autonomous Intelligence-to-Strategy Orchestrator</h3>
              <form className="octa-row" onSubmit={handleExecuteAgent}>
                <input
                  className="octa-input"
                  style={{ flex: 1 }}
                  placeholder="Goal (e.g. Research cloud security market in Germany & generate strategy)"
                  value={orchGoal}
                  onChange={(e) => setOrchGoal(e.target.value)}
                />
                <button className="octa-btn" type="submit">
                  <Sparkles size={14} style={{ marginRight: 6 }} />
                  Run Agent
                </button>
              </form>
              {orchResult && (
                <pre style={{ fontSize: 12, background: "var(--panel-2)", padding: 12, borderRadius: 8, overflowX: "auto" }}>
                  {JSON.stringify(orchResult, null, 2)}
                </pre>
              )}
            </div>
          )}

          {tab === "learning" && (
            <div className="octa-card">
              <h3>Closed-Loop Agent Performance Center</h3>
              <table className="octa-table">
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Task</th>
                    <th>Strategy</th>
                    <th>Reward</th>
                    <th>Success Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {strategies.map((s) => (
                    <tr key={s.id}>
                      <td>{s.agent_name}</td>
                      <td>{s.task_type}</td>
                      <td>{s.strategy_name}</td>
                      <td>{s.weighted_reward_score}</td>
                      <td>{Math.round(s.rolling_success_rate * 100)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
