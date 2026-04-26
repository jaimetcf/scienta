import type { Metadata } from "next";
import "./globals.css";
import "./theme-tokens.css";

export const metadata: Metadata = {
  title: "Scienta",
  description: "Scienta chat UI in Next.js",
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon.ico",
    apple: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
