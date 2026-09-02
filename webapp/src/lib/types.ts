// Mirrors app/market/schemas.py (backend). Keep in sync manually — this is
// a separate codebase from the Python backend, no shared package for MVP.

export interface Candle {
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  close_time: string;
}

export interface Ticker {
  symbol: string;
  price: number;
  price_change_percent_24h: number;
}

export interface MarketState {
  symbol: string;
  tf: string;
  ticker: Ticker;
  candles: Candle[];
  fetched_at: string;
}

// Mirrors app.market.schemas.ALLOWED_TIMEFRAMES.
export const ALLOWED_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;
export type Timeframe = (typeof ALLOWED_TIMEFRAMES)[number];
export const DEFAULT_TIMEFRAME: Timeframe = "1h";

// Mirrors app.market.ws_worker.TRACKED_SYMBOLS (top liquid symbols).
export const TRACKED_SYMBOLS = ["BTC", "ETH", "SOL", "XRP", "BNB"] as const;

// Mirrors app/ai/schemas.py — the AI Reasoning Layer's output. Every number
// here came from the deterministic engines, never from the LLM itself.

export interface ScenarioSplit {
  primary_direction: "long" | "short";
  primary_confidence: number;
  opposite_confidence: number;
  neutral_confidence: number;
}

export interface WhyBullet {
  sign: "+" | "-";
  text: string;
}

export interface AnalysisResult {
  symbol: string;
  tf: string;
  structure_bias: "bullish" | "bearish" | "neutral";
  scenarios: ScenarioSplit | null;
  entry_low: number | null;
  entry_high: number | null;
  invalidation: number | null;
  targets: number[] | null;
  risk_reward: number | null;
  why: WhyBullet[];
  disclaimer: string;
}

// Mirrors app/scanner/schemas.py.

export type ScannerDirection = "long" | "short" | "neutral";
export type RiskLevel = "low" | "medium" | "high";

export interface ScannerEntry {
  symbol: string;
  tf: string;
  direction: ScannerDirection;
  confidence: number;
  risk_reward: number | null;
  risk_level: RiskLevel | null;
  price: number;
}

export interface ScannerResponse {
  entries: ScannerEntry[];
  updated_at: string | null;
}

// Mirrors app/ai/schemas.py's AccuracyReport/AccuracyBreakdownRow.

export interface AccuracyBreakdownRow {
  key: string;
  total_predictions: number;
  win_rate: number | null;
}

export interface AccuracyReport {
  window_days: number;
  total_predictions: number;
  resolved_predictions: number;
  win_rate: number | null;
  avg_realized_r: number | null;
  by_symbol: AccuracyBreakdownRow[];
  by_tf: AccuracyBreakdownRow[];
}
