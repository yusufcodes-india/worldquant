import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { api, SettingsState, CampaignStats } from "./services/api";
import {
  Play,
  Pause,
  StepForward,
  RotateCcw,
  ShieldCheck,
  Activity,
  Layers,
  Code2,
  Table as TableIcon,
  Award,
  BookOpen,
  Settings,
  Download,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Sparkles
} from "lucide-react";
import "./styles.css";

export const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    "overview" | "candidates" | "comparison" | "sprint" | "correlation" | "setup" | "settings"
  >("overview");

  const [settings, setSettings] = useState<SettingsState | null>(null);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [activeCampId, setActiveCampId] = useState<string>("");
  const [stats, setStats] = useState<CampaignStats | null>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [refAlphas, setRefAlphas] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  // AST Live Validator State
  const [testExpr, setTestExpr] = useState(
    "iv_diff = implied_volatility_put_120 - implied_volatility_call_120;\n-group_zscore(iv_diff, subindustry);"
  );
  const [validationOutput, setValidationOutput] = useState<any>(null);

  // Correlation screen state
  const [corrCandidateId, setCorrCandidateId] = useState("");
  const [corrRefId, setCorrRefId] = useState("S1");
  const [corrScreenResult, setCorrScreenResult] = useState<any>(null);

  // Campaign create form state
  const [newCampName, setNewCampName] = useState("Low-Corr Sprint Campaign 01");
  const [newCampProfile, setNewCampProfile] = useState("Low-Corr Sprint");
  const [newCampBudget, setNewCampBudget] = useState(1500);
  const [newCampStopQual, setNewCampStopQual] = useState(false);

  // Settings form state
  const [geminiKeyInput, setGeminiKeyInput] = useState("");
  const [integrationModeInput, setIntegrationModeInput] = useState("MOCK");
  const [tokenInput, setTokenInput] = useState("");

  const refreshAll = async () => {
    try {
      const s = await api.getSettings();
      setSettings(s);
      setIntegrationModeInput(s.integration_mode);

      const camps = await api.listCampaigns();
      setCampaigns(camps);

      let currentId = activeCampId;
      if (!currentId && camps.length > 0) {
        currentId = camps[0].id;
        setActiveCampId(currentId);
      }

      if (currentId) {
        const st = await api.getCampaignStats(currentId);
        setStats(st);
        const cands = await api.listCandidates(currentId, 100);
        setCandidates(cands);
      }

      const refs = await api.listReferenceAlphas();
      setRefAlphas(refs);
    } catch (err: any) {
      setMsg("Connection error: " + err.message);
    }
  };

  useEffect(() => {
    refreshAll();
  }, [activeCampId]);

  const activeCamp = campaigns.find((c) => c.id === activeCampId);

  const handleStep = async () => {
    if (!activeCampId) return;
    setLoading(true);
    try {
      await api.stepCampaign(activeCampId);
      await refreshAll();
    } catch (err: any) {
      setMsg("Step failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRunBatch = async (cycles: number) => {
    if (!activeCampId) return;
    setLoading(true);
    try {
      await api.runBatch(activeCampId, cycles);
      await refreshAll();
    } catch (err: any) {
      setMsg(`Batch run failed: ` + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePause = async () => {
    if (!activeCamp) return;
    setLoading(true);
    try {
      if (activeCamp.status === "running") {
        await api.pauseCampaign(activeCamp.id);
      } else {
        await api.resumeCampaign(activeCamp.id);
      }
      await refreshAll();
    } catch (err: any) {
      setMsg("Toggle pause failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleValidateAST = async () => {
    try {
      const res = await api.validateExpression(testExpr, 8, 4);
      setValidationOutput(res);
    } catch (err: any) {
      setValidationOutput({ is_valid: false, errors: [err.message] });
    }
  };

  const handleRunLocalCorrelation = async () => {
    if (!corrCandidateId || !corrRefId) return;
    try {
      setLoading(true);
      const res = await api.calculateLocalCorrelation(corrCandidateId, corrRefId);
      setCorrScreenResult(res);
    } catch (err: any) {
      setCorrScreenResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCampaign = async () => {
    try {
      setLoading(true);
      const profileData =
        newCampProfile === "Account"
          ? {
              name: "Account",
              max_operators: 64,
              max_fields: 20,
            }
          : {
              name: "Low-Corr Sprint",
              max_operators: 8,
              max_fields: 4,
            };

      const res = await api.createCampaign({
        name: newCampName,
        profile: profileData,
        budget_simulations: newCampBudget,
        stop_on_first_qualifying: newCampStopQual,
      });
      setActiveCampId(res.id);
      await refreshAll();
      setActiveTab("overview");
    } catch (err: any) {
      setMsg("Failed to create campaign: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    try {
      setLoading(true);
      const payload: any = {};
      if (geminiKeyInput.trim()) payload.gemini_api_key = geminiKeyInput.trim();
      if (integrationModeInput) payload.integration_mode = integrationModeInput;
      await api.updateSettings(payload);
      if (tokenInput.trim()) {
        await api.saveToken(tokenInput.trim());
      }
      await refreshAll();
      setMsg("Settings saved successfully.");
    } catch (err: any) {
      setMsg("Save failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!activeCampId) return;
    try {
      const data = await api.exportCampaign(activeCampId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `campaign_${activeCampId}_export.json`;
      a.click();
    } catch (err: any) {
      setMsg("Export failed: " + err.message);
    }
  };

  return (
    <div className="dashboard-container">
      {/* Top Bar */}
      <header className="header">
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Activity className="text-cyan-400" size={20} color="var(--accent-cyan)" />
            <h1 style={{ fontSize: "16px", fontWeight: "700", letterSpacing: "0.02em" }}>
              ALPHA RESEARCH PILOT
            </h1>
          </div>

          {settings && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span className={`badge badge-${settings.integration_mode.toLowerCase()}`}>
                {settings.integration_mode} MODE
              </span>
              {settings.integration_mode === "MOCK" && (
                <span style={{ fontSize: "11px", color: "var(--accent-amber)" }}>
                  (Deterministic Synthetic Platform)
                </span>
              )}
            </div>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {campaigns.length > 0 && (
            <select
              className="input-field"
              style={{ width: "240px", padding: "4px 8px", fontSize: "12px" }}
              value={activeCampId}
              onChange={(e) => setActiveCampId(e.target.value)}
            >
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.status})
                </option>
              ))}
            </select>
          )}

          <button className="btn btn-secondary" style={{ fontSize: "12px" }} onClick={refreshAll}>
            <RotateCcw size={13} /> Refresh
          </button>
        </div>
      </header>

      {/* Tabs */}
      <nav className="tabs">
        <div
          className={`tab-item ${activeTab === "overview" ? "active" : ""}`}
          onClick={() => setActiveTab("overview")}
        >
          Overview & Budgets
        </div>
        <div
          className={`tab-item ${activeTab === "candidates" ? "active" : ""}`}
          onClick={() => setActiveTab("candidates")}
        >
          Candidate Explorer & AST
        </div>
        <div
          className={`tab-item ${activeTab === "comparison" ? "active" : ""}`}
          onClick={() => setActiveTab("comparison")}
        >
          Experiment Comparison
        </div>
        <div
          className={`tab-item ${activeTab === "sprint" ? "active" : ""}`}
          onClick={() => setActiveTab("sprint")}
        >
          Low-Corr Sprint Tracker
        </div>
        <div
          className={`tab-item ${activeTab === "correlation" ? "active" : ""}`}
          onClick={() => setActiveTab("correlation")}
        >
          Self-Correlation & Reference Lib
        </div>
        <div
          className={`tab-item ${activeTab === "setup" ? "active" : ""}`}
          onClick={() => setActiveTab("setup")}
        >
          Campaign Setup
        </div>
        <div
          className={`tab-item ${activeTab === "settings" ? "active" : ""}`}
          onClick={() => setActiveTab("settings")}
        >
          Settings & Security
        </div>
      </nav>

      {/* Content Area */}
      <main style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px", flex: 1 }}>
        {msg && (
          <div
            className="card"
            style={{
              backgroundColor: "rgba(6, 182, 212, 0.1)",
              borderColor: "var(--accent-cyan)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>{msg}</span>
            <button className="btn btn-secondary" style={{ padding: "2px 8px", fontSize: "11px" }} onClick={() => setMsg("")}>
              Dismiss
            </button>
          </div>
        )}

        {/* =========================================================================
            TAB 1: OVERVIEW & BUDGETS
        ========================================================================= */}
        {activeTab === "overview" && activeCamp && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h2 style={{ fontSize: "20px", fontWeight: "700" }}>{activeCamp.name}</h2>
                <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                  Active Profile: <strong>{activeCamp.profile_name}</strong> • Language:{" "}
                  <strong>Fast Expression</strong> • Universe: <strong>TOP3000 (USA)</strong>
                </div>
              </div>

              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  className="btn btn-secondary"
                  onClick={handleStep}
                  disabled={loading || activeCamp.status !== "running"}
                >
                  <StepForward size={14} /> Step (1 Simulation)
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => handleRunBatch(5)}
                  disabled={loading || activeCamp.status !== "running"}
                >
                  <Play size={14} /> Run Batch (5)
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => handleRunBatch(25)}
                  disabled={loading || activeCamp.status !== "running"}
                >
                  <Play size={14} /> Run Batch (25)
                </button>
                <button
                  className={`btn ${activeCamp.status === "running" ? "btn-danger" : "btn-success"}`}
                  onClick={handleTogglePause}
                  disabled={loading}
                >
                  {activeCamp.status === "running" ? (
                    <>
                      <Pause size={14} /> Pause Campaign
                    </>
                  ) : (
                    <>
                      <Play size={14} /> Resume Campaign
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Budget Gauges Grid */}
            <div className="grid-cols-4">
              <div className="card">
                <div style={{ color: "var(--text-muted)", fontSize: "12px", textTransform: "uppercase" }}>
                  Simulation Budget
                </div>
                <div style={{ fontSize: "24px", fontWeight: 700, marginTop: "4px" }}>
                  {activeCamp.submitted_simulations_count} / {activeCamp.budget_simulations}
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                  {activeCamp.budget_simulations - activeCamp.submitted_simulations_count} slots remaining
                </div>
              </div>

              <div className="card">
                <div style={{ color: "var(--text-muted)", fontSize: "12px", textTransform: "uppercase" }}>
                  Qualifying Alphas
                </div>
                <div
                  style={{
                    fontSize: "24px",
                    fontWeight: 700,
                    marginTop: "4px",
                    color: "var(--accent-emerald)",
                  }}
                >
                  {stats?.fully_verified_qualifying_alphas || 0}
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                  Self-Corr &lt; 0.70 & Baseline passed
                </div>
              </div>

              <div className="card">
                <div style={{ color: "var(--text-muted)", fontSize: "12px", textTransform: "uppercase" }}>
                  AI Generation Engine
                </div>
                <div style={{ fontSize: "24px", fontWeight: 700, marginTop: "4px" }}>
                  {settings?.gemini_calls_count || 0} calls
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
                  Model: {settings?.gemini_model} ({settings?.gemini_configured ? "Live Key" : "Mock Fallback"})
                </div>
              </div>

              <div className="card">
                <div style={{ color: "var(--text-muted)", fontSize: "12px", textTransform: "uppercase" }}>
                  Queue State
                </div>
                <div style={{ fontSize: "14px", marginTop: "4px", lineHeight: "1.6" }}>
                  Ready: <strong>{stats?.candidates?.queue_ready || 0}</strong> • Running:{" "}
                  <strong>{stats?.candidates?.queue_running || 0}</strong>
                  <br />
                  Completed: <strong>{stats?.candidates?.queue_completed || 0}</strong> • Uncertain:{" "}
                  <strong style={{ color: "var(--accent-amber)" }}>
                    {stats?.candidates?.queue_uncertain || 0}
                  </strong>
                </div>
              </div>
            </div>

            {/* Quick Candidate Highlights */}
            <div className="card">
              <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px" }}>
                Top Performing Alphas in Active Campaign
              </h3>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Expression</th>
                      <th>Family</th>
                      <th>Main Sharpe</th>
                      <th>Fitness</th>
                      <th>Turnover</th>
                      <th>Sub-Univ Sharpe / Cutoff</th>
                      <th>Self-Corr</th>
                      <th>Readiness Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.slice(0, 5).map((cand) => (
                      <tr key={cand.id}>
                        <td>
                          <code style={{ fontSize: "12px", color: "var(--accent-cyan)" }}>
                            {cand.expression.substring(0, 48)}...
                          </code>
                        </td>
                        <td>{cand.signal_family || "General"}</td>
                        <td>
                          <strong>{cand.simulation_result?.main_sharpe ?? "—"}</strong>
                        </td>
                        <td>{cand.simulation_result?.fitness ?? "—"}</td>
                        <td>
                          {cand.simulation_result?.turnover
                            ? `${(cand.simulation_result.turnover * 100).toFixed(1)}%`
                            : "—"}
                        </td>
                        <td>
                          {cand.simulation_result?.subuniverse_sharpe != null ? (
                            <span>
                              {cand.simulation_result.subuniverse_sharpe} /{" "}
                              {cand.simulation_result.subuniverse_cutoff}{" "}
                              {cand.simulation_result.subuniverse_pass_margin >= 0 ? (
                                <span style={{ color: "var(--accent-emerald)" }}>(Pass)</span>
                              ) : (
                                <span style={{ color: "var(--accent-rose)" }}>(Fail)</span>
                              )}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>
                          {cand.correlations && cand.correlations[0]?.measured_value != null ? (
                            <span
                              style={{
                                color:
                                  cand.correlations[0].measured_value < 0.7
                                    ? "var(--accent-emerald)"
                                    : "var(--accent-rose)",
                              }}
                            >
                              {cand.correlations[0].measured_value.toFixed(2)} (
                              {cand.correlations[0].status})
                            </span>
                          ) : (
                            <span style={{ color: "var(--text-muted)" }}>NOT CHECKED</span>
                          )}
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              cand.readiness_summary === "QUALIFIED_READY_FOR_REVIEW"
                                ? "badge-pass"
                                : "badge-mock"
                            }`}
                          >
                            {cand.readiness_summary}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {candidates.length === 0 && (
                      <tr>
                        <td colSpan={8} style={{ textAlign: "center", padding: "20px", color: "var(--text-muted)" }}>
                          No candidates processed yet. Click 'Step' or 'Run Batch' to begin autonomous research loop.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* =========================================================================
            TAB 2: CANDIDATE EXPLORER & AST INSPECTOR
        ========================================================================= */}
        {activeTab === "candidates" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Live Expression AST Validator */}
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <h3 style={{ fontSize: "14px", fontWeight: 600 }}>Fast Expression AST & Unit Validator</h3>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                  Validates defined variables, field allowlist, operator count & unit consistency
                </span>
              </div>
              <textarea
                className="input-field code-snippet"
                rows={4}
                value={testExpr}
                onChange={(e) => setTestExpr(e.target.value)}
              />
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px" }}>
                <button className="btn btn-primary" onClick={handleValidateAST}>
                  <Code2 size={14} /> Parse & Validate AST
                </button>
                {validationOutput && (
                  <div style={{ display: "flex", gap: "12px", alignItems: "center", fontSize: "12px" }}>
                    <span>
                      Operators: <strong>{validationOutput.estimated_operators}</strong> / 8
                    </span>
                    <span>
                      Fields: <strong>{validationOutput.estimated_fields}</strong> / 4
                    </span>
                    <span>
                      Unit Status: <strong>{validationOutput.unit_status}</strong>
                    </span>
                    <span
                      className={`badge ${validationOutput.is_valid ? "badge-pass" : "badge-fail"}`}
                    >
                      {validationOutput.is_valid ? "VALID" : "INVALID"}
                    </span>
                  </div>
                )}
              </div>
              {validationOutput && validationOutput.errors?.length > 0 && (
                <div style={{ marginTop: "10px", padding: "8px", background: "rgba(244, 63, 94, 0.1)", borderRadius: "6px" }}>
                  <div style={{ color: "var(--accent-rose)", fontWeight: 600, fontSize: "12px" }}>Validation Errors:</div>
                  <ul style={{ paddingLeft: "20px", fontSize: "12px", color: "var(--accent-rose)", marginTop: "4px" }}>
                    {validationOutput.errors.map((e: string, i: number) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Candidates List */}
            <div className="card">
              <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px" }}>
                All Campaign Candidates ({candidates.length})
              </h3>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th>Expression</th>
                      <th>Hypothesis & Design Choice</th>
                      <th>Ops / Fields</th>
                      <th>Main Sharpe</th>
                      <th>Self-Corr</th>
                      <th>Sub-Univ Cutoff</th>
                      <th>Readiness</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((cand) => (
                      <tr key={cand.id}>
                        <td>
                          <span className={`badge ${cand.queue_status === "completed" ? "badge-pass" : "badge-mock"}`}>
                            {cand.queue_status}
                          </span>
                        </td>
                        <td>
                          <code style={{ fontSize: "12px", color: "var(--accent-cyan)" }}>
                            {cand.expression}
                          </code>
                        </td>
                        <td style={{ fontSize: "12px", maxWidth: "260px" }}>
                          <div><strong>{cand.signal_family}:</strong> {cand.hypothesis}</div>
                          {cand.design_change && (
                            <div style={{ color: "var(--text-muted)", marginTop: "2px" }}>
                              Change: {cand.design_change}
                            </div>
                          )}
                        </td>
                        <td>
                          {cand.estimated_operators} ops / {cand.estimated_fields} fields
                        </td>
                        <td>
                          <strong>{cand.simulation_result?.main_sharpe ?? "—"}</strong>
                        </td>
                        <td>
                          {cand.correlations?.[0]?.measured_value ?? "NOT CHECKED"}
                        </td>
                        <td>
                          {cand.simulation_result?.subuniverse_sharpe != null
                            ? `${cand.simulation_result.subuniverse_sharpe} vs ${cand.simulation_result.subuniverse_cutoff}`
                            : "—"}
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              cand.readiness_summary === "QUALIFIED_READY_FOR_REVIEW"
                                ? "badge-pass"
                                : "badge-fail"
                            }`}
                          >
                            {cand.readiness_summary}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 3: EXPERIMENT COMPARISON TABLE
        ========================================================================= */}
        {activeTab === "comparison" && (
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: 600 }}>Multi-Objective Experiment Comparison</h3>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Side-by-side performance, moving sub-universe cutoff, complexity, and self-correlation metrics.
                </div>
              </div>
              <button className="btn btn-secondary" onClick={handleExport}>
                <Download size={13} /> Export Comparison JSON
              </button>
            </div>

            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Expression</th>
                    <th>Main Sharpe</th>
                    <th>Fitness</th>
                    <th>Turnover</th>
                    <th>Sub-Univ Sharpe</th>
                    <th>Sub-Univ Cutoff</th>
                    <th>Pass Margin</th>
                    <th>Self-Corr Value</th>
                    <th>Official Status</th>
                    <th>Fields</th>
                    <th>Ops</th>
                    <th>Sprint Eligible</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((cand) => {
                    const sim = cand.simulation_result;
                    const corr = cand.correlations?.[0];
                    const margin = sim?.subuniverse_pass_margin;
                    return (
                      <tr key={cand.id}>
                        <td>
                          <code style={{ fontSize: "12px", color: "var(--accent-cyan)" }}>
                            {cand.expression.substring(0, 40)}...
                          </code>
                        </td>
                        <td>
                          <strong>{sim?.main_sharpe ?? "—"}</strong>
                        </td>
                        <td>{sim?.fitness ?? "—"}</td>
                        <td>{sim?.turnover ? `${(sim.turnover * 100).toFixed(1)}%` : "—"}</td>
                        <td>{sim?.subuniverse_sharpe ?? "—"}</td>
                        <td>{sim?.subuniverse_cutoff ?? "—"}</td>
                        <td>
                          {margin != null ? (
                            <span style={{ color: margin >= 0 ? "var(--accent-emerald)" : "var(--accent-rose)" }}>
                              {margin >= 0 ? `+${margin}` : margin}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td>
                          {corr?.measured_value != null ? corr.measured_value.toFixed(2) : "—"}
                        </td>
                        <td>
                          <span className={`badge ${corr?.status === "PLATFORM_VERIFIED_PASS" ? "badge-pass" : "badge-mock"}`}>
                            {corr?.status || "NOT CHECKED"}
                          </span>
                        </td>
                        <td>{cand.estimated_fields}</td>
                        <td>{cand.estimated_operators}</td>
                        <td>
                          {cand.is_sprint_eligible ? (
                            <span className="badge badge-pass">QUALIFIED</span>
                          ) : (
                            <span className="badge badge-fail">NON-ELIGIBLE</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 4: LOW-CORR SPRINT TRACKER
        ========================================================================= */}
        {activeTab === "sprint" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div className="card" style={{ borderLeft: "4px solid var(--accent-cyan)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Award size={20} color="var(--accent-cyan)" />
                <h3 style={{ fontSize: "16px", fontWeight: 700 }}>Low-Corr Sprint Competition Rules</h3>
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "6px" }}>
                User-reported competition profile. Strictly enforced locally before simulation dispatch:
              </p>
              <div className="grid-cols-4" style={{ marginTop: "12px" }}>
                <div style={{ background: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "6px" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>MAX FIELDS PER ALPHA</div>
                  <div style={{ fontSize: "18px", fontWeight: 700 }}>&le; 4 Data Fields</div>
                </div>
                <div style={{ background: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "6px" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>MAX OPERATORS PER ALPHA</div>
                  <div style={{ fontSize: "18px", fontWeight: 700 }}>&le; 8 Operators</div>
                </div>
                <div style={{ background: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "6px" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>MIN SUBMISSIONS FOR PRIZE</div>
                  <div style={{ fontSize: "18px", fontWeight: 700 }}>&ge; 10 Submitted Alphas</div>
                </div>
                <div style={{ background: "rgba(0,0,0,0.2)", padding: "10px", borderRadius: "6px" }}>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>RANKING OBJECTIVE</div>
                  <div style={{ fontSize: "14px", fontWeight: 700, marginTop: "4px" }}>
                    Lowest Avg Prod-Corr
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "8px" }}>
                Sprint Qualified Alphas in Campaign ({candidates.filter((c) => c.is_sprint_eligible).length})
              </h3>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Candidate ID</th>
                      <th>Expression</th>
                      <th>Fields (&le; 4)</th>
                      <th>Ops (&le; 8)</th>
                      <th>Sharpe (&ge; 1.25)</th>
                      <th>Fitness (&ge; 1.0)</th>
                      <th>Self-Corr (&lt; 0.70)</th>
                      <th>Sub-Univ Pass</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates
                      .filter((c) => c.is_sprint_eligible)
                      .map((c) => (
                        <tr key={c.id}>
                          <td>{c.id.substring(0, 8)}</td>
                          <td>
                            <code style={{ fontSize: "12px", color: "var(--accent-cyan)" }}>
                              {c.expression}
                            </code>
                          </td>
                          <td>{c.estimated_fields}</td>
                          <td>{c.estimated_operators}</td>
                          <td>{c.simulation_result?.main_sharpe}</td>
                          <td>{c.simulation_result?.fitness}</td>
                          <td>{c.correlations?.[0]?.measured_value}</td>
                          <td>
                            <span className="badge badge-pass">PASSED</span>
                          </td>
                        </tr>
                      ))}
                    {candidates.filter((c) => c.is_sprint_eligible).length === 0 && (
                      <tr>
                        <td colSpan={8} style={{ textAlign: "center", padding: "20px", color: "var(--text-muted)" }}>
                          No candidates currently satisfy all Sprint competition constraints and baseline performance tests.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 5: SELF-CORRELATION & REFERENCE LIBRARY
        ========================================================================= */}
        {activeTab === "correlation" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Local PnL Correlation Screener */}
            <div className="card" style={{ border: "1px solid var(--accent-amber)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--accent-amber)" }}>
                    Local PnL Correlation Screen
                  </h3>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Computes aligned date Pearson correlation. NOT THE PLATFORM SELF-CORRELATION CHECK.
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: "12px", marginTop: "12px", alignItems: "center" }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: "11px", color: "var(--text-muted)" }}>Select Candidate:</label>
                  <select
                    className="input-field"
                    value={corrCandidateId}
                    onChange={(e) => setCorrCandidateId(e.target.value)}
                  >
                    <option value="">-- Choose Candidate --</option>
                    {candidates.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.expression.substring(0, 40)}... (Sharpe: {c.simulation_result?.main_sharpe ?? "N/A"})
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: "11px", color: "var(--text-muted)" }}>Select Reference Alpha:</label>
                  <select
                    className="input-field"
                    value={corrRefId}
                    onChange={(e) => setCorrRefId(e.target.value)}
                  >
                    {refAlphas.map((r) => (
                      <option key={r.id} value={r.id}>
                        Alpha {r.id}: {r.signal_family}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  className="btn btn-primary"
                  style={{ marginTop: "18px" }}
                  onClick={handleRunLocalCorrelation}
                  disabled={loading || !corrCandidateId}
                >
                  Calculate Aligned Correlation
                </button>
              </div>

              {corrScreenResult && (
                <div
                  style={{
                    marginTop: "12px",
                    padding: "12px",
                    background: "rgba(0,0,0,0.3)",
                    borderRadius: "6px",
                    fontSize: "12px",
                  }}
                >
                  <div style={{ color: "var(--accent-amber)", fontWeight: 700, marginBottom: "4px" }}>
                    {corrScreenResult.disclaimer || corrScreenResult.error}
                  </div>
                  {corrScreenResult.signed_correlation != null && (
                    <div className="grid-cols-4" style={{ marginTop: "8px" }}>
                      <div>
                        Signed Correlation: <strong>{corrScreenResult.signed_correlation}</strong>
                      </div>
                      <div>
                        Absolute Correlation: <strong>{corrScreenResult.absolute_correlation}</strong>
                      </div>
                      <div>
                        Overlap Period: <strong>{corrScreenResult.overlap_period}</strong>
                      </div>
                      <div>
                        Trading Days: <strong>{corrScreenResult.observation_count}</strong>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Submitted Reference Library */}
            <div className="card">
              <h3 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "12px" }}>
                Submitted Alpha Reference Library (S1 - S7)
              </h3>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Alpha ID</th>
                      <th>Family</th>
                      <th>Economic Description</th>
                      <th>Expression Seed</th>
                      <th>Status</th>
                      <th>Submitted Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {refAlphas.map((r) => (
                      <tr key={r.id}>
                        <td>
                          <strong>{r.id}</strong>
                        </td>
                        <td>{r.signal_family}</td>
                        <td style={{ fontSize: "12px", maxWidth: "280px" }}>{r.description}</td>
                        <td>
                          <code style={{ fontSize: "11px", color: "var(--accent-cyan)" }}>
                            {r.expression.substring(0, 48)}...
                          </code>
                        </td>
                        <td>
                          <span className="badge badge-mock">{r.status}</span>
                        </td>
                        <td>{r.submitted_date || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 6: CAMPAIGN SETUP
        ========================================================================= */}
        {activeTab === "setup" && (
          <div className="card" style={{ maxWidth: "600px", margin: "0 auto" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "14px" }}>
              Configure New Research Campaign
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "12px", color: "var(--text-muted)" }}>Campaign Name</label>
                <input
                  className="input-field"
                  value={newCampName}
                  onChange={(e) => setNewCampName(e.target.value)}
                />
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "var(--text-muted)" }}>Rule Profile</label>
                <select
                  className="input-field"
                  value={newCampProfile}
                  onChange={(e) => setNewCampProfile(e.target.value)}
                >
                  <option value="Low-Corr Sprint">Low-Corr Sprint (Max 8 ops, Max 4 fields)</option>
                  <option value="Account">Account Profile (Max 64 ops, Max 20 fields)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Maximum Simulation Submissions Budget
                </label>
                <input
                  className="input-field"
                  type="number"
                  value={newCampBudget}
                  onChange={(e) => setNewCampBudget(Number(e.target.value))}
                />
                <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                  Enforced atomically before simulation dispatch. Default: 1,500.
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
                <input
                  type="checkbox"
                  id="stopQual"
                  checked={newCampStopQual}
                  onChange={(e) => setNewCampStopQual(e.target.checked)}
                />
                <label htmlFor="stopQual" style={{ fontSize: "13px" }}>
                  Stop campaign on first fully verified qualifying alpha
                </label>
              </div>

              <button
                className="btn btn-primary"
                style={{ marginTop: "12px" }}
                onClick={handleCreateCampaign}
                disabled={loading}
              >
                Create and Launch Campaign
              </button>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 7: SETTINGS & SECURITY
        ========================================================================= */}
        {activeTab === "settings" && (
          <div className="card" style={{ maxWidth: "640px", margin: "0 auto" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700, marginBottom: "14px" }}>
              Daemon Settings & Security Pairing
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Google Gemini API Key
                </label>
                <input
                  className="input-field"
                  type="password"
                  placeholder="AIzaSy... (Saved securely in local daemon)"
                  value={geminiKeyInput}
                  onChange={(e) => setGeminiKeyInput(e.target.value)}
                />
                <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                  Currently configured:{" "}
                  <strong>{settings?.gemini_configured ? "Yes (Active)" : "No (Mock Fallback)"}</strong>
                </div>
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Integration Mode
                </label>
                <select
                  className="input-field"
                  value={integrationModeInput}
                  onChange={(e) => setIntegrationModeInput(e.target.value)}
                >
                  <option value="MOCK">MOCK (Deterministic synthetic simulations)</option>
                  <option value="MANUAL">MANUAL (Paste / import platform metrics)</option>
                  <option value="LIVE">LIVE (Strictly guarded, explicit user approval required)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Daemon Pairing Token (X-Pilot-Token)
                </label>
                <input
                  className="input-field"
                  type="password"
                  placeholder="Paste 64-character token from .pairing_token"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                />
              </div>

              <button className="btn btn-primary" onClick={handleSaveSettings} disabled={loading}>
                Save Settings
              </button>

              <hr style={{ borderColor: "var(--border-color)", margin: "8px 0" }} />

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600 }}>Export Campaign Data</div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Download campaign JSON with guaranteed secret redaction.
                  </div>
                </div>
                <button className="btn btn-secondary" onClick={handleExport}>
                  <Download size={13} /> Export JSON
                </button>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "8px" }}>
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--accent-rose)" }}>
                    Reset Pilot Database
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                    Wipes all local campaigns, candidates, and simulation records.
                  </div>
                </div>
                <button
                  className="btn btn-danger"
                  onClick={async () => {
                    if (confirm("Are you sure you want to wipe all local research data?")) {
                      await api.resetData();
                      await refreshAll();
                    }
                  }}
                >
                  Reset All Data
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Dashboard />
  </React.StrictMode>
);
