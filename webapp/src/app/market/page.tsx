"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import Link from "next/link";
import { TRACKED_SYMBOLS } from "@/lib/types";

export default function MarketPage() {
  const [query, setQuery] = useState("");
  const router = useRouter();

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      router.push(`/market/${encodeURIComponent(trimmed)}`);
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-6">
      <h1 className="mb-4 text-xl font-semibold">📈 Market</h1>

      <form onSubmit={handleSubmit} className="mb-6 flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Тикер, например BTC"
          className="flex-1 rounded-lg bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          type="submit"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
        >
          Открыть
        </button>
      </form>

      <Link
        href="/scanner"
        className="mb-2 flex items-center justify-between rounded-xl bg-zinc-900 px-4 py-3 hover:bg-zinc-800"
      >
        <span className="font-medium text-zinc-100">🔥 Лучшие сетапы</span>
        <span className="text-zinc-500">→</span>
      </Link>

      <Link
        href="/accuracy"
        className="mb-6 flex items-center justify-between rounded-xl bg-zinc-900 px-4 py-3 hover:bg-zinc-800"
      >
        <span className="font-medium text-zinc-100">📊 Точность AI</span>
        <span className="text-zinc-500">→</span>
      </Link>

      <p className="mb-2 text-sm text-zinc-500">Популярные активы</p>
      <div className="flex flex-wrap gap-2">
        {TRACKED_SYMBOLS.map((symbol) => (
          <Link
            key={symbol}
            href={`/market/${symbol}`}
            className="rounded-full bg-zinc-900 px-4 py-2 text-sm text-zinc-200 hover:bg-zinc-800"
          >
            {symbol}
          </Link>
        ))}
      </div>
    </div>
  );
}
