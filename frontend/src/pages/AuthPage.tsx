import type { FormEvent } from "react";
import { useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { GoogleLogin, type CredentialResponse } from "@react-oauth/google";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";

import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { apiUrl, formatApiErrorDetail } from "../lib/utils";
import { setToken } from "../lib/auth";
import { isGoogleAuthConfigured } from "../providers/AppProviders";

function userFacingNetworkError(msg: string): string {
  if (/failed to fetch|networkerror|load failed/i.test(msg)) {
    return "Could not reach the server. Check your connection and try again.";
  }
  return msg;
}

type AuthResponseUser = {
  profile_complete?: boolean | number;
};

export function AuthPage() {
  const [sp] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const next = sp.get("next")?.startsWith("/") ? sp.get("next")! : "/evaluate";
  const signedOutBanner = Boolean((location.state as { signedOut?: boolean } | null)?.signedOut);

  const [mode, setMode] = useState<"login" | "register">(() =>
    sp.get("mode") === "register" ? "register" : "login"
  );
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const googleOn = isGoogleAuthConfigured();

  function dismissSignedOut() {
    navigate({ pathname: location.pathname, search: location.search, hash: location.hash }, { replace: true, state: {} });
  }

  async function finishWithToken(token: string, user?: AuthResponseUser | null) {
    setToken(token);
    const incomplete =
      user != null && (user.profile_complete === false || user.profile_complete === 0);
    const dest = incomplete
      ? `/profile/setup?next=${encodeURIComponent(next)}`
      : next;
    window.location.assign(dest);
  }

  async function sendGoogleCredential(credential: string) {
    setError("");
    setLoading(true);
    const googleAuthUrl = apiUrl("/api/auth/google");
    try {
      const res = await fetch(googleAuthUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ credential }),
      });
      const text = await res.text();
      let data: { detail?: unknown; token?: unknown; user?: AuthResponseUser } = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = {};
      }
      if (!res.ok) {
        const fromApi = formatApiErrorDetail(data?.detail);
        if (res.status === 404) {
          const generic = !fromApi || /^not\s*found\.?$/i.test(fromApi.trim());
          throw new Error(
            generic ? "Sign-in is temporarily unavailable. Please try again in a moment." : fromApi
          );
        }
        if (res.status === 502 || res.status === 504) {
          throw new Error(fromApi || "The server took too long to respond. Please try again.");
        }
        throw new Error(fromApi || `Google sign-in failed (${res.status})`);
      }
      if (typeof data.token === "string") {
        await finishWithToken(data.token, data.user);
      } else {
        throw new Error(
          "Server replied OK but did not return a token. Check backend logs and that POST /api/auth/google is the CareerLens API."
        );
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Google sign-in failed";
      setError(userFacingNetworkError(msg));
    } finally {
      setLoading(false);
    }
  }

  function onGoogleSuccess(res: CredentialResponse) {
    if (res.credential) void sendGoogleCredential(res.credential);
    else setError("Google did not return a credential.");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const body =
        mode === "login" ? { email, password } : { name, email, password };
      const requestUrl = apiUrl(path);
      const res = await fetch(requestUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(body),
      });
      const text = await res.text();
      let data: { detail?: unknown; token?: unknown; user?: AuthResponseUser } = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = {};
      }
      if (!res.ok) {
        const fromApi = formatApiErrorDetail(data?.detail);
        if (res.status === 404) {
          const generic = !fromApi || /^not\s*found\.?$/i.test(fromApi.trim());
          throw new Error(
            generic ? "Sign-in is temporarily unavailable. Please try again in a moment." : fromApi
          );
        }
        throw new Error(fromApi || `Request failed (${res.status})`);
      }
      if (typeof data.token === "string") await finishWithToken(data.token, data.user);
      else throw new Error("Server returned no token.");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Something went wrong";
      setError(userFacingNetworkError(msg));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="cl-auth-root">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-md"
      >
        <Card className="border-white/20 bg-white/95 shadow-xl shadow-black/20 backdrop-blur-sm">
          <CardHeader className="text-center">
            <p className="text-[0.65rem] font-bold uppercase tracking-[0.2em] text-blue-600">CareerLens</p>
            <CardTitle className="mt-1 text-xl">
              {mode === "login" ? "Sign in" : "Create account"}
            </CardTitle>
            <p className="text-sm text-slate-500">
              {mode === "login" ? "Welcome back." : "Sign up to save reports and run evaluations."}
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {signedOutBanner ? (
              <div className="flex flex-col gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-950">
                <p className="font-medium">You have been signed out.</p>
                <Button type="button" variant="outline" size="sm" className="self-start" onClick={dismissSignedOut}>
                  OK
                </Button>
              </div>
            ) : null}
            {loading ? (
              <div
                className="flex items-center justify-center gap-3 rounded-lg border border-blue-200 bg-blue-50/90 px-4 py-4 text-slate-800"
                role="status"
                aria-live="polite"
              >
                <Loader2 className="h-5 w-5 shrink-0 animate-spin text-blue-600" aria-hidden />
                <div>
                  <p className="text-sm font-semibold">Signing you in…</p>
                  <p className="text-xs text-slate-600">This may take a few seconds. Please do not close this page.</p>
                </div>
              </div>
            ) : null}
            {error ? (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-100">{error}</p>
            ) : null}

            {googleOn ? (
              <div className="space-y-3">
                <p className="text-center text-sm font-medium text-slate-700">Continue with Google</p>
                <p className="text-center text-xs leading-relaxed text-slate-500">
                  One button for <strong>sign up</strong> and <strong>sign in</strong>. If your email is new here, we
                  create your account after you pick your Google account.
                </p>
                <div className="flex min-h-[44px] justify-center [&>div]:w-full [&_iframe]:!mx-auto [&_iframe]:pointer-events-auto">
                  <GoogleLogin
                    onSuccess={onGoogleSuccess}
                    onError={() =>
                      setError("Google closed or blocked the sign-in. Check third-party cookies / extensions, or try another browser.")
                    }
                    useOneTap={false}
                    theme="outline"
                    size="large"
                    text="continue_with"
                    shape="rectangular"
                    width={320}
                  />
                </div>
                <div className="relative py-1">
                  <div className="absolute inset-0 flex items-center" aria-hidden>
                    <div className="w-full border-t border-slate-200" />
                  </div>
                  <div className="relative flex justify-center text-xs font-medium text-slate-400">
                    <span className="bg-white px-2">Or use email</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-center text-xs text-amber-900">
                Google sign-in is not available on this site right now. Use email and password below, or try again
                later.
              </p>
            )}

            <div className="flex rounded-lg bg-slate-100 p-1">
              <button
                type="button"
                className={`flex-1 rounded-md py-2 text-sm font-semibold transition ${
                  mode === "login" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-800"
                }`}
                onClick={() => {
                  setMode("login");
                  setError("");
                }}
              >
                Sign in
              </button>
              <button
                type="button"
                className={`flex-1 rounded-md py-2 text-sm font-semibold transition ${
                  mode === "register" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-800"
                }`}
                onClick={() => {
                  setMode("register");
                  setError("");
                }}
              >
                Sign up
              </button>
            </div>

            <form className="space-y-3" onSubmit={onSubmit}>
              {mode === "register" ? (
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="auth-name">
                    Name
                  </label>
                  <Input
                    id="auth-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    minLength={2}
                    placeholder="Your name"
                    autoComplete="name"
                  />
                </div>
              ) : null}
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="auth-email">
                  Email
                </label>
                <Input
                  id="auth-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="you@company.com"
                  autoComplete="email"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="auth-password">
                  Password
                </label>
                <Input
                  id="auth-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  placeholder="At least 6 characters"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Please wait…" : mode === "login" ? "Sign in with email" : "Create account"}
              </Button>
            </form>

            <p className="text-center text-sm text-slate-500">
              <Link className="font-medium text-blue-600 hover:underline" to="/evaluate">
                ← Back to Evaluate
              </Link>
            </p>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
