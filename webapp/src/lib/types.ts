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
