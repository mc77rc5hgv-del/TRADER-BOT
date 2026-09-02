import Link from "next/link";

import type { Ticker } from "@/lib/types";

function formatPrice(price: number): string {
  return price.toLocaleString("en-US", {
    minimumFractionDigits: price < 10 ? 4 : 2,
    maximumFractionDigits: price < 10 ? 4 : 2,
  });
}

export function PriceCard({ symbol, ticker }: { symbol: string; ticker: Ticker }) {
  const isUp = ticker.price_change_percent_24h >= 0;

  return (
    <Link
      href={`/market/${symbol}`}
      className="flex items-center justify-between rounded-xl bg-zinc-900 px-4 py-3 hover:bg-zinc-800"
    >
      <span className="font-medium text-zinc-100">{symbol}/USDT</span>
      <span className="flex flex-col items-end">
        <span className="text-zinc-100">${formatPrice(ticker.price)}</span>
        <span className={isUp ? "text-sm text-emerald-400" : "text-sm text-red-400"}>
          {isUp ? "+" : ""}
          {ticker.price_change_percent_24h.toFixed(2)}%
        </span>
      </span>
    </Link>
  );
}
