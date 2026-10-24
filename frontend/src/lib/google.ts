// Google sign-in: the backend hands us Google's consent URL plus a signed state
// and PKCE verifier. We keep those in sessionStorage so the callback page can
// prove the redirect belongs to this tab before redeeming the code.
import { api } from "../api/client";
import type { GoogleAuthorization } from "../types";

export type GoogleIntent = "login" | "link";

export interface PendingGoogle {
  intent: GoogleIntent;
  state: string;
  code_verifier: string;
  // Where to land after a successful link.
  returnTo: string;
}

const KEY = "trove_google_pending";

export async function startGoogle(intent: GoogleIntent, returnTo = "/"): Promise<void> {
  const auth = await api.post<GoogleAuthorization>("/api/auth/google/authorize", { intent });
  const pending: PendingGoogle = {
    intent,
    state: auth.state,
    code_verifier: auth.code_verifier,
    returnTo,
  };
  sessionStorage.setItem(KEY, JSON.stringify(pending));
  window.location.assign(auth.authorization_url);
}

// Returns and forgets the pending attempt (each state is single-use in the UI).
export function takePendingGoogle(): PendingGoogle | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    sessionStorage.removeItem(KEY);
    return raw ? (JSON.parse(raw) as PendingGoogle) : null;
  } catch {
    return null;
  }
}
