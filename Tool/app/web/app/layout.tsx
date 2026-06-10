import "./globals.css";
import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";
import { RoleProvider } from "@/components/RoleContext";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Uniqus · CAR Reporting Platform",
  description: "Agentic AI Regulatory Reporting — governed regulatory control cockpit",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <RoleProvider>
            <AppShell>{children}</AppShell>
          </RoleProvider>
        </Providers>
      </body>
    </html>
  );
}
