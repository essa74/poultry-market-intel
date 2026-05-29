"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useState } from "react";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: 2,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="top-center"
        toastOptions={{
          duration: 4000,
          style: {
            background: "#1a1a25",
            color: "#e2e8f0",
            border: "1px solid rgba(255,255,255,0.05)",
            backdropFilter: "blur(12px)",
            borderRadius: "12px",
            fontSize: "14px",
            fontFamily: "var(--font-cairo), sans-serif",
          },
          success: {
            iconTheme: { primary: "#10b981", secondary: "#0a0a0f" },
          },
          error: {
            iconTheme: { primary: "#ef4444", secondary: "#0a0a0f" },
          },
        }}
      />
    </QueryClientProvider>
  );
}
