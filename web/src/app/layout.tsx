import type { Metadata } from "next";
import { Instrument_Sans } from "next/font/google";
import "./globals.css";

import { AppShell } from "@/components/shell/app-shell";

const instrumentSans = Instrument_Sans({
  variable: "--font-instrument-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Marketing OS",
  description: "AI-assisted marketing operating system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={instrumentSans.variable}>
      <body className="antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
