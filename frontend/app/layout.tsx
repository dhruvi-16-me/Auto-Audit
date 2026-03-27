import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AutoAudit AI — Intelligent Invoice Compliance",
  description:
    "AI-powered invoice auditing with real-time compliance detection, investigation, and auto-remediation.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">{children}</body>
    </html>
  );
}
