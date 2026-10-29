import type { Metadata, Viewport } from "next";
import { Noto_Sans, Noto_Sans_Devanagari, Noto_Sans_Telugu } from "next/font/google";
import "./globals.css";

const latin = Noto_Sans({ subsets: ["latin"], weight: ["400", "600", "700", "800"], variable: "--font-latin", display: "swap" });
const telugu = Noto_Sans_Telugu({ subsets: ["telugu"], weight: ["400", "600", "700"], variable: "--font-telugu", display: "swap" });
const deva = Noto_Sans_Devanagari({ subsets: ["devanagari"], weight: ["400", "600", "700"], variable: "--font-deva", display: "swap" });

export const metadata: Metadata = {
  title: "BillSaathi — check a bill before you pay",
  description: "An AI agent that checks Indian bills and payment messages for scams before money moves. Sandbox demo.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0b2239",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${latin.variable} ${telugu.variable} ${deva.variable}`}>
      <body className="min-h-dvh antialiased">{children}</body>
    </html>
  );
}
