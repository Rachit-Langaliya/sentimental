import type { Metadata } from "next";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "SIH Intelligence Platform",
  description: "AI-driven Social Media Analytics Framework for Public Policy Intelligence",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-bg text-ink min-h-screen">
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#1C2D44",
              border: "1px solid #263450",
              color: "#E2E8F0",
            },
          }}
        />
      </body>
    </html>
  );
}
