import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MedClaimIQ",
  description: "Secure medical claims verification, review, and document response"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
