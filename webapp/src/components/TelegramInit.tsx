"use client";

import { useEffect } from "react";

import { authenticateWebApp } from "@/lib/api";
import { getTelegramWebApp } from "@/lib/telegram";

/** Runs once on mount: tells Telegram the app is ready, expands to full
 * height, and validates initData against the backend (TZ section 10 —
 * "Telegram WebApp initData валидируется на backend на каждый запрос", this
 * call establishes the user row up front so later screens don't have to). */
export function TelegramInit() {
  useEffect(() => {
    const webApp = getTelegramWebApp();
    if (!webApp) return; // plain browser during dev — nothing to init

    webApp.ready();
    webApp.expand();

    authenticateWebApp().catch((error: unknown) => {
      console.error("Telegram WebApp auth failed", error);
    });
  }, []);

  return null;
}
