import type { Metadata } from "next";
import { DM_Sans, Fraunces } from "next/font/google";
import { SnackbarProvider } from "@/components/organisms/SnackbarProvider";
import "./globals.css";

const sans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
});

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "PrintDrop",
  description: "Self-hosted print job intake for CUPS",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${sans.variable} ${display.variable} min-h-screen antialiased`}>
        <SnackbarProvider>{children}</SnackbarProvider>
      </body>
    </html>
  );
}
