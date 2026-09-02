// Thin wrapper around the Telegram WebApp JS SDK, loaded via a <script> tag
// in the root layout (https://telegram.org/js/telegram-web-app.js) rather
// than an npm package — Telegram serves and updates it directly, so there's
// no SDK version to pin here.

export interface TelegramWebAppUser {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
}

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { user?: TelegramWebAppUser };
  colorScheme: "light" | "dark";
  themeParams: Record<string, string>;
  ready: () => void;
  expand: () => void;
}

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp };
  }
}

export function getTelegramWebApp(): TelegramWebApp | null {
  if (typeof window === "undefined") return null;
  return window.Telegram?.WebApp ?? null;
}

/** Empty string outside Telegram (e.g. a plain browser during dev) — callers
 * decide how to handle that rather than this module guessing. */
export function getInitData(): string {
  return getTelegramWebApp()?.initData ?? "";
}
