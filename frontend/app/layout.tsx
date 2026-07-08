import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Data Quality Command Center",
  description: "Enterprise data quality monitoring console",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
