import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NetOpsAI",
  description: "AI-powered Network Operations SaaS",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
