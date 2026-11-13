import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { api, SettingsState, CampaignStats } from "./services/api";
import { Play, Pause, StepForward, ExternalLink, ShieldCheck, Activity, Key } from "lucide-react";
import "./styles.css";

export const Popup: React.FC = () => {
  const [paired, setPaired] = useState<boolean | null>(null);
  const [tokenInput, setTokenInput] = useState("");
  const [settings, setSettings] = useState<SettingsState | null>(null);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [activeCamp, setActiveCamp] = useState<any>(null);
  const [stats, setStats] = useState<CampaignStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const refresh = async () => {
    try {
      const pStatus = await api.getPairingStatus();
      setPaired(pStatus.is_paired);
      if (pStatus.is_paired) {
        const s = await api.getSettings();
        setSettings(s);
        const camps = await api.listCampaigns();
        setCampaigns(camps);
        if (camps.length > 0) {
          const current = camps[0];
          setActiveCamp(current);
          const st = await api.getCampaignStats(current.id);
          setStats(st);
        }
      }
    } catch (err: any) {
      setPaired(false);
      setMsg(err.message || "Failed to connect to local daemon.");
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handlePair = async () => {
    try {
      setLoading(true);
      await api.saveToken(tokenInput.trim());
      await api.verifyPairing(tokenInput.trim());
      setPaired(true);
      setMsg("Paired successfully!");
      refresh();
    } catch (err: any) {
      setMsg("Pairing failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const openDashboard = () => {
    if (typeof chrome !== "undefined" && chrome.tabs) {
      chrome.tabs.create({ url: chrome.runtime.getURL("dashboard.html") });
    } else {
      window.open("dashboard.html", "_blank");
    }
  };

  const handleStep = async () => {
    if (!activeCamp) return;
    setLoading(true);
    try {
      await api.stepCampaign(activeCamp.id);
      await refresh();
    } catch (err: any) {
      setMsg("Step failed: " + err.message);
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
      await refresh();
    } catch (err: any) {
      setMsg("Action failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="popup-container">
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ fontSize: "16px", fontWeight: "700" }}>Alpha Research Pilot</h2>
          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>WorldQuant BRAIN Fast Expression</div>
        </div>
        {settings && (
          <span className={`badge badge-${settings.integration_mode.toLowerCase()}`}>
            {settings.integration_mode}
          </span>
        )}
      </div>

      {paired === false && (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--accent-amber)" }}>
            <Key size={16} />
            <strong>Pairing Required</strong>
          </div>
          <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
            Enter the local backend pairing token generated in <code>.pairing_token</code>:
          </p>
          <input
            className="input-field"
            type="password"
            placeholder="Paste 64-char pairing token"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
          />
          <button className="btn btn-primary" onClick={handlePair} disabled={loading}>
            Pair with Local Backend
          </button>
          {msg && <div style={{ fontSize: "11px", color: "var(--accent-rose)" }}>{msg}</div>}
        </div>
      )}

      {paired && activeCamp && (
        <>
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 600, fontSize: "13px" }}>{activeCamp.name}</span>
              <span className={`badge ${activeCamp.status === "running" ? "badge-pass" : "badge-mock"}`}>
                {activeCamp.status}
              </span>
            </div>

            <div className="grid-cols-2" style={{ gap: "8px" }}>
              <div style={{ background: "rgba(0,0,0,0.2)", padding: "8px", borderRadius: "6px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>SUBMISSIONS</div>
                <div style={{ fontSize: "15px", fontWeight: 700 }}>
                  {stats?.submitted_simulations_count || 0} / {activeCamp.budget_simulations}
                </div>
              </div>
              <div style={{ background: "rgba(0,0,0,0.2)", padding: "8px", borderRadius: "6px" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>QUALIFIED ALPHAS</div>
                <div style={{ fontSize: "15px", fontWeight: 700, color: "var(--accent-emerald)" }}>
                  {stats?.fully_verified_qualifying_alphas || 0}
                </div>
              </div>
            </div>

            <div style={{ fontSize: "11px", color: "var(--text-muted)", display: "flex", justifyContent: "space-between" }}>
              <span>Profile: <strong>{activeCamp.profile_name}</strong></span>
              <span>Gemini: <strong>{settings?.gemini_configured ? "Ready" : "Mock Fallback"}</strong></span>
            </div>
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            <button className="btn btn-secondary" style={{ flex: 1 }} onClick={handleStep} disabled={loading}>
              <StepForward size={14} /> Step
            </button>
            <button className="btn btn-secondary" style={{ flex: 1 }} onClick={handleTogglePause} disabled={loading}>
              {activeCamp.status === "running" ? <><Pause size={14} /> Pause</> : <><Play size={14} /> Resume</>}
            </button>
          </div>
        </>
      )}

      {paired && !activeCamp && (
        <div className="card" style={{ textAlign: "center", padding: "20px" }}>
          <p style={{ color: "var(--text-muted)", fontSize: "12px", marginBottom: "12px" }}>No campaigns initialized.</p>
          <button className="btn btn-primary" onClick={openDashboard}>
            Launch Dashboard to Create Campaign
          </button>
        </div>
      )}

      <button className="btn btn-primary" style={{ marginTop: "auto" }} onClick={openDashboard}>
        <ExternalLink size={14} /> Open Full Research Dashboard
      </button>

      <div style={{ fontSize: "10px", color: "var(--text-muted)", textAlign: "center" }}>
        Local-first daemon on 127.0.0.1:8765 • Zero telemetry
      </div>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Popup />
  </React.StrictMode>
);
