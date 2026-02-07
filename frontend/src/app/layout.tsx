import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { ReactQueryProvider } from "@/lib/react-query";
import Header from "@/components/layout/Header";
import CommandPalette from "@/components/ui/command-palette";
import KeyboardShortcuts from "@/components/ui/keyboard-shortcuts";

export const metadata: Metadata = {
  title: "STOCK_SCREENER.EXE - Terminal Market Analysis",
  description: "Advanced stock screener with backtesting and ML features",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        <ReactQueryProvider>
          <Suspense fallback={<div className="h-16 border-b border-border bg-card" />}>
            <Header />
          </Suspense>
          <main className="min-h-screen">{children}</main>
          <CommandPalette />
          <KeyboardShortcuts />
        </ReactQueryProvider>
      </body>
    </html>
  );
}
