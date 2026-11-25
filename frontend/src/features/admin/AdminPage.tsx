import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, RefreshCw, ShieldAlert } from "lucide-react";
import { apiFetch, ApiError } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import type {
  ScholarshipVersion,
  SourceCheckLogItem,
  SourceItem,
} from "../../types/api";

export function AdminPage() {
  const queryClient = useQueryClient();
  const [syncMsg, setSyncMsg] = useState<string | null>(null);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [newSource, setNewSource] = useState({
    name: "",
    owner_provider: "",
    url: "",
    source_type: "official_pdf",
    collection_method: "http_pdf",
    check_interval_hours: 24,
  });

  const { data: sources } = useQuery<SourceItem[]>({
    queryKey: ["admin", "sources"],
    queryFn: () => apiFetch<SourceItem[]>("/admin/sources"),
  });

  const { data: logs } = useQuery<SourceCheckLogItem[]>({
    queryKey: ["admin", "source-logs"],
    queryFn: () => apiFetch<SourceCheckLogItem[]>("/admin/source-logs?limit=25"),
  });

  const { data: versions } = useQuery<ScholarshipVersion[]>({
    queryKey: ["admin", "versions"],
    queryFn: () => apiFetch<ScholarshipVersion[]>("/admin/versions"),
  });

  const syncAllMutation = useMutation({
    mutationFn: () =>
      apiFetch<{
        sources_checked: number;
        sources_succeeded: number;
        sources_failed: number;
        changes_detected: number;
        scholarships_updated: number;
        documents_reindexed: number;
      }>("/admin/sync", { method: "POST" }),
    onSuccess: (res) => {
      setErrMsg(null);
      setSyncMsg(
        `Checked ${res.sources_checked} official source(s): ${res.sources_succeeded} succeeded, ${res.sources_failed} failed, ${res.scholarships_updated} scheme(s) auto-updated, ${res.documents_reindexed} document(s) indexed.`
      );
      queryClient.invalidateQueries({ queryKey: ["admin"] });
      queryClient.invalidateQueries({ queryKey: ["scholarships"] });
    },
    onError: (err) => {
      setErrMsg(err instanceof ApiError ? err.message : "Sync failed.");
    },
  });

  const addSourceMutation = useMutation({
    mutationFn: () =>
      apiFetch("/admin/sources", {
        method: "POST",
        body: JSON.stringify(newSource),
      }),
    onSuccess: () => {
      setNewSource({
        name: "",
        owner_provider: "",
        url: "",
        source_type: "official_pdf",
        collection_method: "http_pdf",
        check_interval_hours: 24,
      });
      setErrMsg(null);
      queryClient.invalidateQueries({ queryKey: ["admin", "sources"] });
    },
    onError: (err) => setErrMsg(err instanceof ApiError ? err.message : "Could not add source."),
  });

  const reviewVersionMutation = useMutation({
    mutationFn: (versionId: string) =>
      apiFetch(`/admin/versions/${versionId}/review`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "versions"] });
      queryClient.invalidateQueries({ queryKey: ["scholarships"] });
    },
  });

  const handleAddSource = (e: FormEvent) => {
    e.preventDefault();
    addSourceMutation.mutate();
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Admin Source Registry &amp; Verification
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Trigger live official-source checks, inspect version diffs, and manage monitored
            official URLs.
          </p>
        </div>

        <button
          type="button"
          onClick={() => syncAllMutation.mutate()}
          disabled={syncAllMutation.isPending}
          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${syncAllMutation.isPending ? "animate-spin" : ""}`} />
          {syncAllMutation.isPending ? "Syncing live official sources..." : "Sync Official Sources Now"}
        </button>
      </div>

      {syncMsg && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          {syncMsg}
        </div>
      )}
      {errMsg && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {errMsg}
        </div>
      )}

      {/* Official Sources */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
        <h2 className="text-lg font-bold text-slate-900">
          Registered Official Sources ({sources?.length ?? 0})
        </h2>

        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-xs">
            <thead className="border-b border-slate-200 text-slate-500">
              <tr>
                <th className="py-2 pr-4">Source</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Last Checked</th>
                <th className="py-2 pr-4">Status / Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(sources ?? []).map((src) => (
                <tr key={src.id}>
                  <td className="py-2.5 pr-4">
                    <p className="font-semibold text-slate-900">{src.name}</p>
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-700 hover:underline break-all"
                    >
                      {src.url}
                    </a>
                  </td>
                  <td className="py-2.5 pr-4 text-slate-600">{src.source_type}</td>
                  <td className="py-2.5 pr-4 text-slate-600">
                    {formatDateTime(src.last_checked_at)}
                  </td>
                  <td className="py-2.5 pr-4">
                    {src.last_error ? (
                      <span className="inline-flex items-center gap-1 text-rose-700">
                        <ShieldAlert className="h-3.5 w-3.5" />
                        {src.last_error.slice(0, 80)}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-emerald-700">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Healthy
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <form onSubmit={handleAddSource} className="grid gap-3 border-t border-slate-100 pt-4 sm:grid-cols-4">
          <input
            type="text"
            required
            value={newSource.name}
            onChange={(e) => setNewSource({ ...newSource, name: e.target.value })}
            placeholder="Source title"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            type="text"
            required
            value={newSource.owner_provider}
            onChange={(e) => setNewSource({ ...newSource, owner_provider: e.target.value })}
            placeholder="Official provider"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            type="url"
            required
            value={newSource.url}
            onChange={(e) => setNewSource({ ...newSource, url: e.target.value })}
            placeholder="https://official.gov.in/guideline.pdf"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={addSourceMutation.isPending}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
          >
            Add Official Source
          </button>
        </form>
      </section>

      {/* Change History */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
        <h2 className="text-lg font-bold text-slate-900">Scholarship Version Audit Log</h2>
        <div className="space-y-3">
          {(versions ?? []).map((v) => (
            <div
              key={v.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-4 text-xs"
            >
              <div>
                <p className="font-semibold text-slate-900">
                  Version {v.version_number} • Source: {v.change_source}
                </p>
                <p className="mt-0.5 text-slate-500">
                  Changed fields: {Object.keys(v.changed_fields).join(", ") || "none"} •{" "}
                  {formatDateTime(v.created_at)}
                </p>
              </div>
              {v.reviewed ? (
                <span className="rounded-full bg-emerald-50 px-2.5 py-1 font-semibold text-emerald-800">
                  Reviewed ({v.reviewed_by || "auto"})
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => reviewVersionMutation.mutate(v.id)}
                  className="rounded-lg bg-amber-600 px-3 py-1.5 font-semibold text-white hover:bg-amber-700"
                >
                  Mark Reviewed &amp; Verified
                </button>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Recent Check Logs */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
        <h2 className="text-lg font-bold text-slate-900">Recent Source Check Logs</h2>
        <div className="space-y-2 text-xs">
          {(logs ?? []).map((l) => (
            <div
              key={l.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2"
            >
              <span>
                <strong>{formatDateTime(l.checked_at)}</strong> — {l.summary || l.error_message}
              </span>
              <span className={l.success ? "font-semibold text-emerald-700" : "font-semibold text-rose-700"}>
                {l.success ? `HTTP ${l.http_status ?? "OK"}` : "FAILED"}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
