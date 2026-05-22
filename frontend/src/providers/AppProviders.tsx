import type { ReactNode } from "react";
import { GoogleOAuthProvider } from "@react-oauth/google";

const clientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined)?.trim() ?? "";

export function AppProviders({ children }: { children: ReactNode }) {
  if (clientId) {
    return <GoogleOAuthProvider clientId={clientId}>{children}</GoogleOAuthProvider>;
  }
  return <>{children}</>;
}

export function isGoogleAuthConfigured(): boolean {
  return Boolean(clientId);
}
