export type ActivePosition = {
  ticker: string;
  net_qty: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl_pct: number;
  last_decision?: {
    rec?: string;
    signal_score?: number;
    prob_outperform_90d?: number;
    what_changed_since_last?: string[];
  } | null;
  sell_trigger: boolean;
  sell_reason: string;
};

export type AnalyzeResponse = {
  evidence_packet: Record<string, unknown>;
  llm_decision: {
    rec: string;
    signal_score: number;
    prob_outperform_90d: number;
    horizon_days: number;
    key_drivers: string[];
    key_risks: string[];
    disconfirming_evidence: string[];
    what_changed_since_last?: string[];
    exit_triggers: string[];
  };
};

export type MetricsResponse = {
  equity_curve: Array<{ date: string; value: number }>;
  sharpe: number;
  max_drawdown: number;
  win_rate: number;
};

const DEFAULT_BACKEND_URL = "http://localhost:8000";

export function getBackendUrl(): string {
  return process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL;
}

export async function fetchJson<T>(path: string): Promise<T> {
  const base = getBackendUrl();
  const res = await fetch(`${base}${path}`, { cache: "no-store" });
  if (!res.ok) {
    const message = await safeErrorMessage(res);
    throw new Error(message || `Request failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function postJson<T>(path: string, payload: Record<string, unknown>): Promise<T> {
  const base = getBackendUrl();
  const res = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const message = await safeErrorMessage(res);
    throw new Error(message || `Request failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

async function safeErrorMessage(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: string };
    return data?.detail || "";
  } catch {
    return "";
  }
}
