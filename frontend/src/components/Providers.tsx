"use client";

import { TokenProvider } from "@/lib/tokenContext";

export default function Providers({ children }: { children: React.ReactNode }) {
  return <TokenProvider>{children}</TokenProvider>;
}
