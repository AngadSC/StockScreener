import type { Metadata } from "next";
import Script from "next/script";
import { Suspense } from "react";
import "./globals.css";
import { ReactQueryProvider } from "@/lib/react-query";
import { AuthProvider } from "@/lib/auth";
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
      <head>
        <Script id="gtm" strategy="beforeInteractive">
          {`(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-KFDJ78MV');`}
        </Script>
      </head>
      <body className="min-h-screen">
        <noscript>
          <iframe
            src="https://www.googletagmanager.com/ns.html?id=GTM-KFDJ78MV"
            height="0"
            width="0"
            style={{ display: "none", visibility: "hidden" }}
          />
        </noscript>
        <ReactQueryProvider>
          <AuthProvider>
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
          </AuthProvider>
        </ReactQueryProvider>
      </body>
    </html>
  );
}
