import { useCallback, useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";

import { Button } from "../components/ui/button";
import { apiUrl } from "../lib/utils";
import { authHeaders, clearToken, getToken } from "../lib/auth";

export function DashboardLayout() {
  const navigate = useNavigate();
  const loc = useLocation();
  const [hasToken, setHasToken] = useState(() => !!getToken());
  const [profileGate, setProfileGate] = useState<"unknown" | "complete" | "incomplete">(() =>
    getToken() ? "unknown" : "complete"
  );
  const [logoutOpen, setLogoutOpen] = useState(false);

  const closeLogoutModal = useCallback(() => setLogoutOpen(false), []);

  useEffect(() => {
    if (!logoutOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeLogoutModal();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [logoutOpen, closeLogoutModal]);

  function confirmLogout() {
    clearToken();
    setHasToken(false);
    setProfileGate("complete");
    setLogoutOpen(false);
    navigate("/login", { state: { signedOut: true } });
  }

  useEffect(() => {
    if (!hasToken) {
      setProfileGate("complete");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(apiUrl("/api/profile"), {
          headers: { Accept: "application/json", ...authHeaders() },
        });
        if (cancelled) return;
        if (res.status === 401) {
          clearToken();
          setHasToken(false);
          setProfileGate("complete");
          return;
        }
        if (!res.ok) {
          setProfileGate("complete");
          return;
        }
        const j = (await res.json()) as { profile?: { profile_complete?: boolean } };
        if (cancelled) return;
        setProfileGate(j.profile?.profile_complete ? "complete" : "incomplete");
      } catch {
        if (!cancelled) setProfileGate("complete");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [hasToken, loc.pathname]);

  useEffect(() => {
    if (!hasToken || profileGate === "unknown" || profileGate === "complete") return;
    if (loc.pathname === "/profile/setup") return;
    navigate(
      `/profile/setup?next=${encodeURIComponent(loc.pathname + loc.search || "/evaluate")}`,
      { replace: true }
    );
  }, [hasToken, profileGate, loc.pathname, loc.search, navigate]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(apiUrl("/status"));
        const data = res.ok ? ((await res.json()) as { auth_required?: boolean }) : {};
        if (cancelled) return;
        if (data.auth_required && !getToken()) {
          navigate(`/login?next=${encodeURIComponent(loc.pathname + loc.search)}`, { replace: true });
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [navigate, loc.pathname, loc.search]);

  return (
    <div className="cl-page-wrap">
      <div className="cl-header-shell">
        <header className="cl-header">
          <div className="cl-brand">CAREERLENS</div>
          <nav className="cl-header-links">
            <Link to="/evaluate">Evaluate</Link>
            <Link to="/reports">Reports</Link>
            {hasToken ? (
              <Link to="/profile">Profile</Link>
            ) : null}
            <a href={apiUrl("/status")} target="_blank" rel="noreferrer">
              Status
            </a>
            {hasToken ? (
              <button type="button" onClick={() => setLogoutOpen(true)}>
                Log out
              </button>
            ) : (
              <Link to={`/login?next=${encodeURIComponent(loc.pathname || "/evaluate")}`}>Log in</Link>
            )}
          </nav>
        </header>
      </div>
      <main className="cl-main">
        {hasToken && profileGate === "unknown" ? (
          <div className="cl-form-panel py-20 text-center text-sm text-slate-600">Checking your session…</div>
        ) : (
          <Outlet />
        )}
      </main>

      {logoutOpen ? (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center p-4"
          role="presentation"
        >
          <button
            type="button"
            className="absolute inset-0 cursor-default bg-slate-950/55 backdrop-blur-[2px]"
            aria-label="Dismiss"
            onClick={closeLogoutModal}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="logout-dialog-title"
            className="relative z-[1] w-full max-w-md rounded-xl border border-slate-200/80 bg-white p-6 shadow-2xl shadow-black/20"
          >
            <h2 id="logout-dialog-title" className="text-lg font-semibold tracking-tight text-slate-900">
              Log out?
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              Do you want to log out? You will need to sign in again to access your account.
            </p>
            <div className="mt-6 flex flex-wrap justify-end gap-2">
              <Button type="button" variant="outline" onClick={closeLogoutModal}>
                No, stay signed in
              </Button>
              <Button type="button" variant="default" onClick={confirmLogout}>
                Yes, log out
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
