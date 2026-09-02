"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  href: string;
  label: string;
  icon: string;
  /** Screens not built yet (later steps of the Phase 1 sequence) render
   * disabled rather than linking somewhere that doesn't exist. */
  enabled: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Home", icon: "🏠", enabled: true },
  { href: "/market", label: "Market", icon: "📈", enabled: true },
  { href: "/ai", label: "AI", icon: "✨", enabled: false },
  { href: "/profile", label: "Profile", icon: "👤", enabled: false },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 inset-x-0 border-t border-zinc-800 bg-zinc-950/95 backdrop-blur">
      <ul className="flex justify-around">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

          if (!item.enabled) {
            return (
              <li key={item.href} className="flex-1">
                <span className="flex flex-col items-center gap-0.5 py-2.5 text-xs text-zinc-600">
                  <span className="text-lg opacity-50">{item.icon}</span>
                  {item.label}
                </span>
              </li>
            );
          }

          return (
            <li key={item.href} className="flex-1">
              <Link
                href={item.href}
                className={`flex flex-col items-center gap-0.5 py-2.5 text-xs ${
                  isActive ? "text-blue-400" : "text-zinc-400"
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
