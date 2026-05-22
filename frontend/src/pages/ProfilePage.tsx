import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { authHeaders } from "../lib/auth";
import { apiUrl, cn, formatApiErrorDetail } from "../lib/utils";

import type { UserProfile } from "../types/profile";

const MAX_AVATAR_BYTES = 280 * 1024;
const fieldClass =
  "min-h-[100px] w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500";

export function ProfilePage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");
  const [error, setError] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [bio, setBio] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);

  async function load() {
    setError("");
    setSavedMsg("");
    const res = await fetch(apiUrl("/api/profile"), { headers: { Accept: "application/json", ...authHeaders() } });
    const text = await res.text();
    let data: { profile?: UserProfile; detail?: unknown } = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = {};
    }
    if (!res.ok) {
      throw new Error(formatApiErrorDetail(data.detail) || "Could not load your profile.");
    }
    const p = data.profile;
    if (!p) throw new Error("Invalid profile response.");
    setEmail(p.email || "");
    setName(p.name || "");
    setPhone(p.phone || "");
    setJobTitle(p.job_title || "");
    setBio(p.bio || "");
    setAvatarUrl(p.avatar_url || null);
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Could not load profile.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function onPickAvatar(e: React.ChangeEvent<HTMLInputElement>) {
    setError("");
    setSavedMsg("");
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Please choose an image file (PNG, JPEG, GIF, or WebP).");
      e.target.value = "";
      return;
    }
    if (file.size > MAX_AVATAR_BYTES) {
      setError("Image is too large. Please use a photo under about 280 KB.");
      e.target.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const r = reader.result;
      if (typeof r === "string") setAvatarUrl(r);
    };
    reader.readAsDataURL(file);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSavedMsg("");
    setSaving(true);
    try {
      const patchBody: Record<string, unknown> = {
        name: name.trim(),
        phone: phone.trim(),
        job_title: jobTitle.trim(),
        bio: bio.trim(),
      };
      if (avatarUrl !== null) {
        patchBody.avatar_url = avatarUrl;
      }
      const res = await fetch(apiUrl("/api/profile"), {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Accept: "application/json", ...authHeaders() },
        body: JSON.stringify(patchBody),
      });
      const text = await res.text();
      let data: { detail?: unknown } = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        data = {};
      }
      if (!res.ok) {
        throw new Error(formatApiErrorDetail(data.detail) || "Could not save profile.");
      }
      setSavedMsg("Profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="cl-form-panel flex items-center justify-center gap-3 py-16 text-slate-600">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" aria-hidden />
        <span>Loading your profile…</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="cl-hero">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Your profile</h1>
        <p className="mt-2 text-sm text-slate-600">Update how you appear in CareerLens.</p>
      </div>

      <form className="cl-form-panel space-y-4" onSubmit={onSubmit}>
        {error ? <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-100">{error}</p> : null}
        {savedMsg ? (
          <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">{savedMsg}</p>
        ) : null}

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="prof-name">
            Display name <span className="text-red-500">*</span>
          </label>
          <Input id="prof-name" value={name} onChange={(ev) => setName(ev.target.value)} required minLength={2} maxLength={120} />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="prof-email">
            Email
          </label>
          <Input id="prof-email" value={email} readOnly disabled className="bg-slate-50 text-slate-500" />
          <p className="mt-1 text-xs text-slate-500">Email is tied to your sign-in.</p>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="prof-phone">
            Phone <span className="text-slate-400">(optional)</span>
          </label>
          <Input
            id="prof-phone"
            value={phone}
            onChange={(ev) => setPhone(ev.target.value)}
            maxLength={40}
            placeholder="+1 555 123 4567"
            autoComplete="tel"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="prof-job">
            Job title <span className="text-slate-400">(optional)</span>
          </label>
          <Input id="prof-job" value={jobTitle} onChange={(ev) => setJobTitle(ev.target.value)} maxLength={160} placeholder="e.g. Software Engineer" />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="prof-bio">
            Short bio <span className="text-slate-400">(optional)</span>
          </label>
          <textarea
            id="prof-bio"
            className={cn(fieldClass)}
            value={bio}
            onChange={(ev) => setBio(ev.target.value)}
            maxLength={4000}
            rows={4}
            placeholder="A few lines about you…"
          />
        </div>

        <div>
          <span className="mb-1 block text-xs font-medium text-slate-600">Profile photo</span>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-full border border-slate-200 bg-slate-50 text-xs text-slate-400">
              {avatarUrl ? (
                <img src={avatarUrl} alt="" className="h-full w-full object-cover" />
              ) : (
                <span>No photo</span>
              )}
            </div>
            <div className="min-w-0 flex-1">
              <input
                type="file"
                accept="image/png,image/jpeg,image/gif,image/webp"
                className="text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-blue-600 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white hover:file:bg-blue-700"
                onChange={onPickAvatar}
              />
              <p className="mt-1 text-xs text-slate-500">PNG, JPEG, GIF, or WebP, under ~280 KB.</p>
              {avatarUrl ? (
                <button
                  type="button"
                  className="mt-2 text-xs font-semibold text-red-600 hover:underline"
                  onClick={() => setAvatarUrl("")}
                >
                  Remove photo
                </button>
              ) : null}
            </div>
          </div>
        </div>

        <div className="pt-2">
          <Button type="submit" disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
                Saving…
              </>
            ) : (
              "Save changes"
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
