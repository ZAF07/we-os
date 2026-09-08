import type { Metadata } from "next";
import { Instrument_Sans } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

const instrumentSans = Instrument_Sans({
  variable: "--font-instrument-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: { default: "We-OS", template: "%s · We-OS" },
  description:
    "Augmented workflow for digital marketing. Strategy before content, with your judgement kept in.",
};

/**
 * The root layout: the document, the font, and the Clerk session.
 *
 * It renders no chrome of its own. The `(app)` group adds the app shell and the
 * `(public)` group adds the top bar and footer, so which half a page belongs to
 * is decided by where it lives.
 *
 * Args:
 *   children: The active route group's layout.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en" className={instrumentSans.variable}>
        <body className="antialiased">{children}</body>
      </html>
    </ClerkProvider>
  );
}
