// API Service for communicating with local Python backend (127.0.0.1:8765)

export interface SettingsState {
  app_name: string;
  version: string;
  host: string;
  port: number;
  integration_mode: string;
  adapter_mode: string;
  gemini_configured: boolean;
  gemini_model: string;
  gemini_calls_count: number;
  gemini_tokens_used: number;
  gemini_is_paused: boolean;
  feature_flag_tab_observation: boolean;
  auth_info: any;
  capabilities: any;
}

export interface CampaignStats {
  campaign_id: string;
  status: string;
  budget_simulations: number;
  submitted_simulations_count: number;
  candidates: {
    total_candidates: number;
    validation_passed: number;
    validation_failed: number;
    queue_ready: number;
    queue_running: number;
    queue_completed: number;
    queue_failed: number;
    queue_uncertain: number;
  };
  fully_verified_qualifying_alphas: number;
}

export class ApiClient {
  private baseUrl: string = "http://127.0.0.1:8765";
  private token: string = "";

  constructor() {
    this.loadToken();
  }

  async loadToken(): Promise<string> {
    return new Promise((resolve) => {
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        chrome.storage.local.get(["pilot_token", "pilot_url"], (res) => {
          if (res.pilot_token) this.token = res.pilot_token;
          if (res.pilot_url) this.baseUrl = res.pilot_url;
          resolve(this.token);
        });
      } else {
        const stored = localStorage.getItem("pilot_token");
        if (stored) this.token = stored;
        resolve(this.token);
      }
    });
  }

  async saveToken(token: string, url: string = "http://127.0.0.1:8765") {
    this.token = token;
    this.baseUrl = url;
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      await chrome.storage.local.set({ pilot_token: token, pilot_url: url });
    } else {
      localStorage.setItem("pilot_token", token);
      localStorage.setItem("pilot_url", url);
    }
  }

  private async request(endpoint: string, options: RequestInit = {}): Promise<any> {
    await this.loadToken();
    const headers = new Headers(options.headers || {});
    headers.set("Content-Type", "application/json");
    if (this.token) {
      headers.set("X-Pilot-Token", this.token);
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `HTTP Error ${response.status}`);
    }

    return response.json();
  }

  async getPairingStatus() {
    return this.request("/pairing/status");
  }

  async verifyPairing(token: string) {
    return this.request("/pairing/verify", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  }

  async getSettings(): Promise<SettingsState> {
    return this.request("/settings");
  }

  async updateSettings(data: any) {
    return this.request("/settings", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async listCampaigns() {
    return this.request("/campaigns");
  }

  async createCampaign(data: any) {
    return this.request("/campaigns", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getCampaignStats(campaignId: string): Promise<CampaignStats> {
    return this.request(`/campaigns/${campaignId}/stats`);
  }

  async pauseCampaign(campaignId: string) {
    return this.request(`/campaigns/${campaignId}/pause`, { method: "POST" });
  }

  async resumeCampaign(campaignId: string) {
    return this.request(`/campaigns/${campaignId}/resume`, { method: "POST" });
  }

  async stepCampaign(campaignId: string) {
    return this.request(`/campaigns/${campaignId}/step`, { method: "POST" });
  }

  async runBatch(campaignId: string, cycles: number = 5) {
    return this.request(`/campaigns/${campaignId}/run_batch?cycles=${cycles}`, { method: "POST" });
  }

  async listCandidates(campaignId: string, limit: number = 50) {
    return this.request(`/candidates?campaign_id=${campaignId}&limit=${limit}`);
  }

  async validateExpression(expression: string, maxOps: number = 8, maxFields: number = 4) {
    return this.request("/candidates/validate", {
      method: "POST",
      body: JSON.stringify({ expression, max_operators: maxOps, max_fields: maxFields }),
    });
  }

  async listReferenceAlphas() {
    return this.request("/reference_library");
  }

  async addReferenceAlpha(alpha: any) {
    return this.request("/reference_library", {
      method: "POST",
      body: JSON.stringify(alpha),
    });
  }

  async calculateLocalCorrelation(candidateId: string, referenceAlphaId: string) {
    return this.request("/correlations/local_screen", {
      method: "POST",
      body: JSON.stringify({ candidate_id: candidateId, reference_alpha_id: referenceAlphaId }),
    });
  }

  async getPairwiseMatrix(campaignId: string) {
    return this.request(`/correlations/pairwise_matrix?campaign_id=${campaignId}`);
  }

  async exportCampaign(campaignId: string) {
    return this.request(`/data/export/${campaignId}`);
  }

  async resetData() {
    return this.request("/data/reset", { method: "POST" });
  }
}

export const api = new ApiClient();
