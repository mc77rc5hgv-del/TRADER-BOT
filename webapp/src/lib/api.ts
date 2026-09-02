import { getInitData } from "./telegram";
import type { AnalysisResult, MarketState } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const initData = getInitData();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      ...(initData ? { Authorization: `tma ${initData}` } : {}),
    },
  });

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new ApiError(response.status, body || response.statusText);
  }

  return (await response.json()) as T;
}

export function getMarketState(symbol: string, tf: string): Promise<MarketState> {
  const params = new URLSearchParams({ tf });
  return request<MarketState>(`/market/${encodeURIComponent(symbol)}/state?${params}`);
}

export function authenticateWebApp(): Promise<{ ok: boolean }> {
  return request("/webapp/auth", { method: "POST" });
}

export function analyzeSymbol(symbol: string, tf: string): Promise<AnalysisResult> {
  return request<AnalysisResult>("/webapp/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, tf }),
  });
}
