import { useCallback, useEffect, useRef, useState } from "react";

import { EvaluationReport, type EvaluationReportData } from "../components/report/EvaluationReport";
import { authHeaders } from "../lib/auth";
import { apiUrl, formatApiErrorDetail } from "../lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

type ReportItem = {
  id: number;
  candidate_name: string;
  github_url: string;
  linkedin_url: string;
  target_role: string;
  is_intern: boolean;
  final_score: number;
  data_completeness: number;
  created_at: string;
  report?: EvaluationReportData;
};

type DeleteDialogState = {
  ids: number[];
  summary: string;
};

export function ReportsPage() {
  const [items, setItems] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [deleteDialog, setDeleteDialog] = useState<DeleteDialogState | null>(null);
  const errorRef = useRef<HTMLParagraphElement | null>(null);

  const loadReports = useCallback(async () => {
    setError("");
    const res = await fetch(apiUrl("/api/reports?limit=100"), { headers: { Accept: "application/json", ...authHeaders() } });
    const text = await res.text();
    let data: { items?: ReportItem[]; detail?: unknown } = {};
    if (text) {
      try {
        data = JSON.parse(text) as typeof data;
      } catch {
        throw new Error("Invalid response from server.");
      }
    }
    if (!res.ok) throw new Error(formatApiErrorDetail(data.detail) || "Failed to load reports");
    setItems(Array.isArray(data.items) ? data.items : []);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        await loadReports();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unexpected error");
      } finally {
        setLoading(false);
      }
    })();
  }, [loadReports]);

  useEffect(() => {
    if (error && errorRef.current) {
      errorRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [error]);

  useEffect(() => {
    if (!deleteDialog) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) setDeleteDialog(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [deleteDialog, busy]);

  function toggleSelect(id: number) {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  const deleteByIds = async (ids: number[]) => {
    if (ids.length === 0) return;
    const uniqueIds = [...new Set(ids.map((n) => Number(n)))].filter((n) => Number.isFinite(n));
    if (uniqueIds.length === 0) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const res = await fetch(apiUrl("/api/reports/delete"), {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ ids: uniqueIds }),
      });
      const text = await res.text();
      let payload: { detail?: unknown; deleted?: number[]; missing?: number[] } = {};
      if (text) {
        try {
          payload = JSON.parse(text) as typeof payload;
        } catch {
          /* ignore */
        }
      }
      if (!res.ok) {
        throw new Error(
          formatApiErrorDetail(payload.detail) ||
            text?.slice(0, 200) ||
            `Delete failed (${res.status}). Restart the API so it includes POST /api/reports/delete.`,
        );
      }
      setSelectedIds((prev) => prev.filter((id) => !uniqueIds.includes(id)));
      try {
        await loadReports();
      } catch {
        setItems((prev) => prev.filter((x) => !uniqueIds.includes(x.id)));
      }
      const n = payload.deleted?.length ?? uniqueIds.length;
      setNotice(n === 1 ? "Report deleted." : `${n} reports deleted.`);
      window.setTimeout(() => setNotice(""), 4000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Delete failed";
      setError(
        msg.includes("Failed to fetch") || msg.includes("NetworkError")
          ? `${msg} Start the API from the backend folder (python -m app.main) and keep VITE_API_BASE_URL as http://localhost:8000 or leave it empty for the dev proxy.`
          : msg,
      );
    } finally {
      setBusy(false);
    }
  };

  const openDeleteOne = (r: ReportItem) => {
    setDeleteDialog({
      ids: [r.id],
      summary: `${r.candidate_name} (report #${r.id})`,
    });
  };

  const openDeleteBulk = () => {
    const n = selectedIds.length;
    if (n === 0) return;
    setDeleteDialog({
      ids: [...selectedIds],
      summary: `${n} selected report${n === 1 ? "" : "s"}`,
    });
  };

  const runConfirmedDelete = async () => {
    if (!deleteDialog) return;
    const ids = deleteDialog.ids;
    setDeleteDialog(null);
    await deleteByIds(ids);
  };

  return (
    <div className="relative space-y-3">
      {deleteDialog ? (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 p-4"
          role="presentation"
          tabIndex={-1}
          onClick={() => !busy && setDeleteDialog(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-dialog-title"
            className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="delete-dialog-title" className="text-lg font-bold text-slate-900">
              Delete report?
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              This permanently removes <span className="font-semibold text-slate-800">{deleteDialog.summary}</span>{" "}
              from the database. You cannot undo this.
            </p>
            <div className="mt-6 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                disabled={busy}
                className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                onClick={() => setDeleteDialog(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                className="rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
                onClick={() => void runConfirmedDelete()}
              >
                {busy ? "Deleting…" : "Delete permanently"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Previous candidate reports</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-600">
          {loading ? "Loading reports..." : `Total reports: ${items.length}`}
        </CardContent>
      </Card>

      {notice ? (
        <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-900">
          {notice}
        </p>
      ) : null}

      {selectedIds.length > 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm">
          <span className="font-medium text-red-900">
            {selectedIds.length} report{selectedIds.length === 1 ? "" : "s"} selected
          </span>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              className="rounded-md bg-red-600 px-3 py-1.5 font-semibold text-white shadow-sm hover:bg-red-700 disabled:opacity-60"
              onClick={openDeleteBulk}
            >
              Delete selected
            </button>
            <button
              type="button"
              disabled={busy}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              onClick={() => setSelectedIds([])}
            >
              Clear selection
            </button>
          </div>
        </div>
      ) : null}

      {error ? (
        <p
          ref={errorRef}
          className="rounded-md bg-red-50 p-3 text-sm text-red-600 ring-1 ring-red-200"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      {!loading && items.length === 0 ? (
        <Card>
          <CardContent className="p-5 text-sm text-slate-600">No reports yet. Evaluate a candidate first.</CardContent>
        </Card>
      ) : null}
      {items.map((r) => (
        <Card key={r.id}>
          <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 space-y-0 pb-3">
            <div className="flex min-w-0 items-start gap-3">
              <input
                type="checkbox"
                className="cl-report-select mt-1 h-4 w-4 shrink-0 rounded border-slate-300 accent-red-600"
                checked={selectedIds.includes(r.id)}
                disabled={busy}
                onChange={() => toggleSelect(r.id)}
                aria-label={`Select ${r.candidate_name}`}
              />
              <CardTitle className="leading-snug">{r.candidate_name}</CardTitle>
            </div>
            <button
              type="button"
              disabled={busy}
              className="shrink-0 rounded-md border border-red-200 bg-white px-3 py-1.5 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                openDeleteOne(r);
              }}
            >
              Delete
            </button>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <p>
              Role: <strong>{r.target_role}</strong> {r.is_intern ? "(Intern)" : ""}
            </p>
            <p>
              Final score: <strong>{Number(r.final_score).toFixed(1)}</strong>
            </p>
            <p>
              Data completeness: <strong>{Math.round(Number(r.data_completeness) * 100)}%</strong>
            </p>
            <p>GitHub: {r.github_url}</p>
            <p>LinkedIn: {r.linkedin_url}</p>
            <p className="text-slate-500">Created: {new Date(r.created_at).toLocaleString()}</p>
            {r.report && Object.keys(r.report).length > 0 ? (
              <details className="mt-4 rounded-lg border border-slate-200 bg-slate-50/80 p-3">
                <summary className="cursor-pointer text-sm font-semibold text-slate-800">
                  Full report (same as Evaluate page)
                </summary>
                <div className="cl-report mt-3 border-0 bg-white p-0 shadow-none">
                  <EvaluationReport data={r.report} />
                </div>
              </details>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
