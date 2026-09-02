import type { Metadata } from "next";
import Script from "next/script";

import { BottomNav } from "@/components/BottomNav";
import { TelegramInit } from "@/components/TelegramInit";

import "./globals.css";

export const metadata: Metadata = {
  title: "TRADE AI",
  description: "AI-платформа для трейдинга внутри Telegram",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ru" className="h-full">
      <body className="flex min-h-full flex-col bg-zinc-950 text-zinc-50 antialiased">
        <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
        <TelegramInit />
        <main className="flex-1 overflow-y-auto pb-20">{children}</main>
        <BottomNav />
      </body>
    </html>
  );
}
