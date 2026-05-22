import type { FormEvent } from "react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";

import { EvaluationReport, type EvaluationReportData } from "../components/report/EvaluationReport";
import { authHeaders } from "../lib/auth";
import { apiUrl } from "../lib/utils";

type AnalyzeResponse = {
  analysis?: {
    highlights?: string[];
    activity_tier_90d?: string;
    enrichment_tier?: string;
    full_name?: string;
  };
};

type ProfilePreview = {
  github?: AnalyzeResponse;
  linkedin?: AnalyzeResponse;
};

async function parseJsonResponse<T>(res: Response): Promise<T> {
  const contentType = res.headers.get("content-type") || "";
  const text = await res.text();
  let data = {} as T;
  if (text && contentType.includes("application/json")) {
    data = JSON.parse(text) as T;
  }
  if (!res.ok) {
    const detail =
      (data as { detail?: string }).detail ||
      (text ? text.slice(0, 280) : "") ||
      `Request failed (${res.status}).`;
    throw new Error(detail);
  }
  return data;
}

export function EvaluatePage() {
  const [github, setGithub] = useState("");
  const [linkedin, setLinkedin] = useState("");
  const [role, setRole] = useState("Software Engineer");
  const [isIntern, setIsIntern] = useState(true);
  const [loading, setLoading] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [preview, setPreview] = useState<ProfilePreview | null>(null);
  const [result, setResult] = useState<EvaluationReportData | null>(null);
  const [error, setError] = useState("");

  async function loadProfilePreview() {
    setError("");
    setPreview(null);
    setPreviewLoading(true);
    try {
      const headers = {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...authHeaders(),
      };
      const [ghRes, liRes] = await Promise.all([
        fetch(apiUrl("/api/analyze/github"), {
          method: "POST",
          headers,
          body: JSON.stringify({ github_url: github.trim() }),
        }),
        fetch(apiUrl("/api/analyze/linkedin"), {
          method: "POST",
          headers,
          body: JSON.stringify({ linkedin_url: linkedin.trim() }),
        }),
      ]);
      const [gh, li] = await Promise.all([
        parseJsonResponse<AnalyzeResponse>(ghRes),
        parseJsonResponse<AnalyzeResponse>(liRes),
      ]);
      setPreview({ github: gh, linkedin: li });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const res = await fetch(apiUrl("/api/evaluate"), {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json", ...authHeaders() },
        body: JSON.stringify({
          github_url: github,
          linkedin_url: linkedin,
          target_role: role,
          is_intern: isIntern,
        }),
      });
      const data = await parseJsonResponse<EvaluationReportData>(res);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <section className="cl-hero">
        <div className="cl-blob cl-blob-a"></div>
        <div className="cl-blob cl-blob-b"></div>
        <div className="cl-blob cl-blob-c"></div>
        <h1>
          Rich profiles deserve a <span>clear score</span> -
          <br />
          GitHub &amp; LinkedIn in one pass
        </h1>
        <p>Paste two profile links and your target role.</p>
      </section>

      <form className="cl-form-panel" onSubmit={onSubmit}>
        <div className="cl-url-bar">
          <input
            value={github}
            onChange={(e) => setGithub(e.target.value)}
            placeholder="https://github.com/username"
            required
          />
          <input
            value={linkedin}
            onChange={(e) => setLinkedin(e.target.value)}
            placeholder="https://www.linkedin.com/in/..."
            required
          />
          <button disabled={loading} type="submit">{loading ? "Evaluating..." : "Evaluate"}</button>
        </div>
        <div className="cl-hints">
          <span>GitHub: user or org root · LinkedIn: must include /in/</span>
          <button
            type="button"
            className="cl-link-btn"
            disabled={previewLoading || !github.trim() || !linkedin.trim()}
            onClick={() => void loadProfilePreview()}
          >
            {previewLoading ? "Checking profiles…" : "Preview profile signals"}
          </button>
          <Link to="/reports">View reports</Link>
        </div>
        <div className="cl-role-row">
          <div className="cl-role-field">
            <label htmlFor="target-role" className="cl-role-label">
              Target role
            </label>
            <input
              id="target-role"
              name="target_role"
              type="text"
              className="cl-role-input"
              autoComplete="organization-title"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="e.g. Software Engineer"
            />
          </div>
          <label className="cl-intern-label">
            <input type="checkbox" checked={isIntern} onChange={(e) => setIsIntern(e.target.checked)} />
            Intern candidate
          </label>
        </div>
      </form>

      {preview ? (
        <section className="cl-preview-panel">
          <h3 className="cl-report-heading">Profile preview</h3>
          {preview.github?.analysis?.highlights?.length ? (
            <div className="cl-section">
              <h4>
                GitHub
                {preview.github.analysis.activity_tier_90d ? (
                  <span className="cl-pill" style={{ marginLeft: "0.5rem" }}>
                    {preview.github.analysis.activity_tier_90d}
                  </span>
                ) : null}
              </h4>
              <ul className="cl-list">
                {preview.github.analysis.highlights.map((line) => (
                  <li key={`prev-gh-${line}`}>{line}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {preview.linkedin?.analysis?.highlights?.length ? (
            <div className="cl-section">
              <h4>
                LinkedIn
                {preview.linkedin.analysis.enrichment_tier ? (
                  <span className="cl-pill" style={{ marginLeft: "0.5rem" }}>
                    {preview.linkedin.analysis.enrichment_tier}
                  </span>
                ) : null}
              </h4>
              <ul className="cl-list">
                {preview.linkedin.analysis.highlights.map((line) => (
                  <li key={`prev-li-${line}`}>{line}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      {loading ? (
        <section className="cl-loading-panel" aria-busy="true" aria-live="polite">
          <div className="cl-loading-spinner" aria-hidden />
          <div className="cl-loading-copy">
            <p className="cl-loading-title">Generating your report…</p>
            <p className="cl-loading-sub">
              Pulling public GitHub &amp; LinkedIn signals, scoring categories, and running the narrative
              analysis. This often takes 30–90 seconds.
            </p>
            <div className="cl-loading-skeleton">
              <div className="cl-skel-line cl-skel-line-lg" />
              <div className="cl-skel-line" />
              <div className="cl-skel-line cl-skel-line-sm" />
            </div>
          </div>
        </section>
      ) : null}

      {error ? <p className="cl-error">{error}</p> : null}
      {result ? (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <section className="cl-report">
            <EvaluationReport data={result} />
          </section>
        </motion.div>
      ) : null}
    </div>
  );
} 
  