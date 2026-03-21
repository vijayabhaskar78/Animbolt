import type { Metadata } from "next";
import { Syne, DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import QueryProvider from "@/providers/QueryProvider";
import Navbar from "@/components/Navbar";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  weight: ["300", "400", "500"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AnimBolt — AI Animation Studio",
  description: "Transform ideas into animated mathematics with AI and Manim.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${syne.variable} ${dmSans.variable} ${jetbrainsMono.variable}`}
    >
      <body>
        <QueryProvider>
          <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
            <Navbar />
            <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
              {children}
            </div>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
