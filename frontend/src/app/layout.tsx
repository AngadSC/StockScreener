import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { ReactQueryProvider } from "@/lib/react-query";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
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
      <body className="min-h-screen">
        <ReactQueryProvider>
          <div className="flex min-h-screen flex-col">
            <Suspense fallback={<div className="h-20 border-b border-border bg-card" />}>
              <Header />
            </Suspense>
            <div className="flex-1">
              <PageTransition>
                <main className="min-h-full">{children}</main>
              </PageTransition>
            </div>
            <Footer />
          </div>
          <CommandPalette />
          <KeyboardShortcuts />
        </ReactQueryProvider>
      </body>
    </html>
  );
}
