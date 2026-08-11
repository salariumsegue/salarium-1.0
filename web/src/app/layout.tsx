import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "./globals.css";

import SiteFooter from "@/components/site-footer";
import SiteHeader from "@/components/site-header";
import { SITE_URL } from "@/lib/site-config";
import { loadReleaseSnapshot } from "@/lib/site-data";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Salarium — Autonomous Equity Research",
    template: "%s | Salarium",
  },
  description:
    "An open-source systematic equity research platform combining walk-forward machine learning, concentrated portfolio construction, covariance-aware weighting, and governed risk controls.",
  applicationName: "Salarium",
  authors: [{ name: "Niall Gillen" }],
  creator: "Niall Gillen",
  publisher: "Salarium",
  category: "Finance and quantitative research",
  keywords: [
    "quantitative finance",
    "equity research",
    "machine learning",
    "portfolio construction",
    "walk-forward backtest",
    "risk management",
    "open source",
  ],
  alternates: { canonical: "/" },
  manifest: "/manifest.webmanifest",
  icons: {
    icon: "/salarium-mark.svg",
    shortcut: "/salarium-mark.svg",
    apple: "/salarium-mark.svg",
  },
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "Salarium",
    title: "Salarium — Autonomous Equity Research",
    description:
      "Transparent quantitative equity research from governed data to signal-aware portfolio construction.",
    images: [{ url: "/opengraph-image", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Salarium — Autonomous Equity Research",
    description:
      "Transparent quantitative equity research from governed data to signal-aware portfolio construction.",
    images: ["/opengraph-image"],
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  colorScheme: "dark",
  themeColor: "#000000",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const release = loadReleaseSnapshot();
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "Salarium",
    applicationCategory: "FinanceApplication",
    operatingSystem: "Web",
    description: metadata.description,
    url: SITE_URL,
    author: {
      "@type": "Person",
      name: "Niall Gillen",
    },
    codeRepository: "https://github.com/salariumsegue/salarium-1.0",
    softwareVersion: release.release.version,
    isAccessibleForFree: true,
  };

  return (
    <html lang="en" className="h-full bg-black">
      <body className="min-h-full bg-black antialiased">
        <a href="#main-content" className="skip-link">Skip to content</a>
        <div className="grid-overlay pointer-events-none fixed inset-0 z-0" aria-hidden="true" />
        <div className="ambient-glow pointer-events-none fixed inset-0 z-0" aria-hidden="true" />
        <div className="relative z-10 flex min-h-screen flex-col">
          <SiteHeader version={release.release.version} status={release.release.status} />
          <div className="flex-1">{children}</div>
          <SiteFooter commit={release.provenance.git_commit} generatedAt={release.generated_at_utc} />
        </div>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
        />
      </body>
    </html>
  );
}
