type BreakdownEntry = { score?: number; weight?: number };

export type EvaluationReportData = {
  final_score?: number;
  data_completeness?: number;
  category_breakdown?: Record<string, BreakdownEntry>;
  strengths?: string[];
  weaknesses?: string[];
  hiring_recommendations?: string[];
  suggested_role_fit?: string[];
  generated_signals?: {
    tech_depth_score?: number;
    consistency_score?: number;
    open_source_contribution_signal?: number;
    career_progression_score?: number;
    skill_relevance_score?: number;
  };
  intern_criteria?: Record<string, number>;
  github_signals?: {
    commit_activity_index_90d?: number | null;
    repos_pushed_90d?: number | null;
    public_push_commits_estimated_90d?: number | null;
    commits_repo_scan_90d?: number | null;
    public_repo_count?: number | null;
  };
  linkedin_signals?: {
    experience_years?: number | null;
    skills_count?: number | null;
    achievements_count?: number | null;
    career_progression_score?: number | null;
    skill_relevance_score?: number | null;
    data_completeness?: number | null;
  };
  linkedin_enrichment_tier?: string;
  profile_highlights?: {
    github?: string[];
    linkedin?: string[];
  };
  warnings?: string[];
};

function titleCase(text: string) {
  return (text || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function fmtNum(v: unknown) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number" && Number.isFinite(v)) return String(v);
  return String(v);
}

function ProgressRow({ label, score }: { label: string; score: number }) {
  const w = Math.max(0, Math.min(100, score));
  return (
    <div className="cl-progress-row">
      <div className="cl-progress-head">
        <span>{label}</span>
        <span>{score.toFixed(1)} / 100</span>
      </div>
      <div className="cl-bar">
        <div className="cl-bar-fill" style={{ width: `${w}%` }} />
      </div>
    </div>
  );
}

export function EvaluationReport({ data }: { data: EvaluationReportData }) {
  const signals = data.generated_signals || {};
  const breakdown = data.category_breakdown || {};
  const intern = data.intern_criteria || {};
  const internEntries = Object.entries(intern).filter(([, v]) => typeof v === "number");

  return (
    <div className="cl-report-inner">
      <h3 className="cl-report-heading">Your report</h3>

      <section className="cl-top-grid">
        <div className="cl-stat">
          <div className="cl-stat-label">Final score</div>
          <div className="cl-stat-value">{Number(data.final_score || 0).toFixed(1)} / 100</div>
        </div>
        <div className="cl-stat">
          <div className="cl-stat-label">Data completeness</div>
          <div className="cl-stat-value">{Math.round(Number(data.data_completeness || 0) * 100)}%</div>
        </div>
        <div className="cl-stat">
          <div className="cl-stat-label">Tech depth signal</div>
          <div className="cl-stat-value">{Number(signals.tech_depth_score || 0).toFixed(1)}</div>
        </div>
      </section>

      <div className="cl-section">
        <h4>Weighted category breakdown</h4>
        {Object.keys(breakdown).length === 0 ? (
          <p className="cl-mini-placeholder">No breakdown available.</p>
        ) : (
          Object.entries(breakdown).map(([key, value]) => {
            const score = Number(value?.score || 0);
            const pct = Math.round(Number(value?.weight || 0) * 100);
            return (
              <ProgressRow
                key={key}
                label={`${titleCase(key)} (${pct}%)`}
                score={score}
              />
            );
          })
        )}
      </div>

      <div className="cl-section">
        <h4>Strengths</h4>
        {(data.strengths?.length ?? 0) > 0 ? (
          <ul>
            {data.strengths!.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        ) : (
          <p className="cl-mini-placeholder">No items.</p>
        )}
      </div>

      <div className="cl-section">
        <h4>Weaknesses</h4>
        {(data.weaknesses?.length ?? 0) > 0 ? (
          <ul>
            {data.weaknesses!.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        ) : (
          <p className="cl-mini-placeholder">No items.</p>
        )}
      </div>

      <div className="cl-section">
        <h4>Hiring recommendations</h4>
        {(data.hiring_recommendations?.length ?? 0) > 0 ? (
          <ul>
            {data.hiring_recommendations!.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        ) : (
          <p className="cl-mini-placeholder">No items.</p>
        )}
      </div>

      <div className="cl-section">
        <h4>Suggested role fit</h4>
        <div className="cl-pill-wrap">
          {(data.suggested_role_fit?.length ?? 0) > 0 ? (
            data.suggested_role_fit!.map((role) => (
              <span key={role} className="cl-pill">
                {role}
              </span>
            ))
          ) : (
            <span className="cl-pill">No role suggestion</span>
          )}
        </div>
      </div>

      <div className="cl-section">
        <h4>Generated signals</h4>
        <div className="cl-pill-wrap">
          <span className="cl-pill">Consistency: {Number(signals.consistency_score || 0).toFixed(1)}</span>
          <span className="cl-pill">
            Open source: {Number(signals.open_source_contribution_signal || 0).toFixed(1)}
          </span>
          <span className="cl-pill">
            Career progression: {Number(signals.career_progression_score || 0).toFixed(1)}
          </span>
          <span className="cl-pill">
            Skill relevance: {Number(signals.skill_relevance_score || 0).toFixed(1)}
          </span>
        </div>
      </div>

      {data.github_signals ? (
        <div className="cl-section">
          <h4>GitHub activity (public API only)</h4>
          <div className="cl-pill-wrap">
            <span className="cl-pill">
              Activity index (90d): {fmtNum(data.github_signals.commit_activity_index_90d)}
            </span>
            <span className="cl-pill">Repos pushed (90d): {fmtNum(data.github_signals.repos_pushed_90d)}</span>
            <span className="cl-pill">
              Push commits est. (90d): {fmtNum(data.github_signals.public_push_commits_estimated_90d)}
            </span>
            <span className="cl-pill">
              Repo scan commits (90d): {fmtNum(data.github_signals.commits_repo_scan_90d)}
            </span>
            <span className="cl-pill">Public repos listed: {fmtNum(data.github_signals.public_repo_count)}</span>
          </div>
        </div>
      ) : null}

      {data.linkedin_signals ? (
        <div className="cl-section">
          <h4>
            LinkedIn signals
            {data.linkedin_enrichment_tier ? (
              <span className="cl-pill" style={{ marginLeft: "0.5rem" }}>
                {data.linkedin_enrichment_tier}
              </span>
            ) : null}
          </h4>
          <div className="cl-pill-wrap">
            <span className="cl-pill">Experience (yrs): {fmtNum(data.linkedin_signals.experience_years)}</span>
            <span className="cl-pill">Skills: {fmtNum(data.linkedin_signals.skills_count)}</span>
            <span className="cl-pill">Achievements: {fmtNum(data.linkedin_signals.achievements_count)}</span>
            <span className="cl-pill">
              Career score: {fmtNum(data.linkedin_signals.career_progression_score)}
            </span>
            <span className="cl-pill">
              Skill score: {fmtNum(data.linkedin_signals.skill_relevance_score)}
            </span>
            <span className="cl-pill">
              Data completeness:{" "}
              {data.linkedin_signals.data_completeness != null
                ? `${Math.round(Number(data.linkedin_signals.data_completeness) * 100)}%`
                : "—"}
            </span>
          </div>
        </div>
      ) : null}

      {data.profile_highlights &&
      (data.profile_highlights.github?.length || data.profile_highlights.linkedin?.length) ? (
        <div className="cl-section">
          <h4>Profile highlights</h4>
          {data.profile_highlights.github?.length ? (
            <>
              <p className="cl-role-label">GitHub</p>
              <ul className="cl-list">
                {data.profile_highlights.github.map((line) => (
                  <li key={`gh-${line}`}>{line}</li>
                ))}
              </ul>
            </>
          ) : null}
          {data.profile_highlights.linkedin?.length ? (
            <>
              <p className="cl-role-label">LinkedIn</p>
              <ul className="cl-list">
                {data.profile_highlights.linkedin.map((line) => (
                  <li key={`li-${line}`}>{line}</li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      ) : null}

      {internEntries.length > 0 ? (
        <div className="cl-section">
          <h4>Intern evaluation criteria</h4>
          {internEntries.map(([key, value]) => (
            <ProgressRow key={key} label={titleCase(key)} score={Number(value)} />
          ))}
        </div>
      ) : null}

      {(data.warnings?.length ?? 0) > 0 ? (
        <div className="cl-warn cl-warn-block">
          <strong>Warnings:</strong>
          <ul>
            {data.warnings!.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
