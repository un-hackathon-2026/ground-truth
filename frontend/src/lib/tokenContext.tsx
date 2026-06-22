"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

export interface UsageInfo {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  estimated_cost_usd?: number;
}

interface TokenContextValue {
  totalTokens: number;
  promptTokens: number;
  completionTokens: number;
  estimatedCostUsd: number;
  addUsage: (u: UsageInfo) => void;
}

const TokenContext = createContext<TokenContextValue>({
  totalTokens: 0,
  promptTokens: 0,
  completionTokens: 0,
  estimatedCostUsd: 0,
  addUsage: () => {},
});

export function TokenProvider({ children }: { children: ReactNode }) {
  const [promptTokens, setPromptTokens] = useState(0);
  const [completionTokens, setCompletionTokens] = useState(0);
  const [estimatedCostUsd, setEstimatedCostUsd] = useState(0);

  const addUsage = useCallback((u: UsageInfo) => {
    if (!u) return;
    setPromptTokens((p) => p + (u.prompt_tokens ?? 0));
    setCompletionTokens((c) => c + (u.completion_tokens ?? 0));
    setEstimatedCostUsd((e) => e + (u.estimated_cost_usd ?? 0));
  }, []);

  return (
    <TokenContext.Provider
      value={{
        totalTokens: promptTokens + completionTokens,
        promptTokens,
        completionTokens,
        estimatedCostUsd,
        addUsage,
      }}
    >
      {children}
    </TokenContext.Provider>
  );
}

export function useTokens() {
  return useContext(TokenContext);
}
