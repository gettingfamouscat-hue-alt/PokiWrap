import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PokiWrap — Poki games as desktop apps",
  description: "Download PokiWrap for Windows or macOS. Wrap Poki games into native desktop apps with cloud progress and an ad blocker.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
