import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { ReactQueryProvider } from "@/lib/react-query";
import Header from "@/components/layout/Header";
import CommandPalette from "@/components/ui/command-palette";
import KeyboardShortcuts from "@/components/ui/keyboard-shortcuts";
import PageTransition from "@/components/layout/PageTransition";

export const metadata: Metadata = {
  title: "QuantorSignal",
  description: "Luxury market intelligence with stock screening and portfolio backtesting.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body>
        <ReactQueryProvider>
          <Suspense fallback={<div className="h-20 border-b border-border bg-card" />}>
            <Header />
          </Suspense>
          <PageTransition>
            <main className="min-h-screen">{children}</main>
          </PageTransition>
          <CommandPalette />
          <KeyboardShortcuts />
        </ReactQueryProvider>
      </body>
    </html>
  );
}
