import type { Metadata } from "next";
import { Suspense } from "react";
import { Josefin_Sans, Marcellus } from "next/font/google";
import "./globals.css";
import { ReactQueryProvider } from "@/lib/react-query";
import Header from "@/components/layout/Header";
import CommandPalette from "@/components/ui/command-palette";
import KeyboardShortcuts from "@/components/ui/keyboard-shortcuts";

const displayFont = Marcellus({
  subsets: ["latin"],
  variable: "--font-display",
  weight: "400",
});

const bodyFont = Josefin_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600", "700"],
});

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
      <body className={`${displayFont.variable} ${bodyFont.variable}`}>
        <ReactQueryProvider>
          <Suspense fallback={<div className="h-20 border-b border-border bg-card" />}>
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
