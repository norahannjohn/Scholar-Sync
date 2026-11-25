import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, Trash2 } from "lucide-react";
import { apiFetch } from "../../lib/api";
import { formatDate, formatDateTime, TRACKING_STATUS_OPTIONS } from "../../lib/format";
import type { ApplicationProgressStatus, StudentApplication } from "../../types/api";

export function TrackerPage() {
  const queryClient = useQueryClient();
  const [editingNotes, setEditingNotes] = useState<Record<string, string>>({});

  const { data: apps, isLoading } = useQuery<StudentApplication[]>({
    queryKey: ["applications"],
    queryFn: () => apiFetch<StudentApplication[]>("/applications"),
  });

  const patchMutation = useMutation({
    mutationFn: ({
      id,
      status,
      notes,
    }: {
      id: string;
      status?: ApplicationProgressStatus;
      notes?: string;
    }) =>
      apiFetch(`/applications/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status, notes }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/applications/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Application Tracker</h1>
        <p className="mt-1 text-sm text-slate-600">
          Statuses below are <strong>user-maintained personal tracking notes</strong> — ScholarSync
          never submits applications or reads private status from government portals.
        </p>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
          Loading tracked applications...
        </div>
      ) : !apps || apps.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center">
          <p className="text-base font-semibold text-slate-900">No tracked applications yet</p>
          <p className="mt-1 text-sm text-slate-600">
            Open any scholarship detail page and click &quot;Track Progress&quot; to manage your
            checklist and submission notes.
          </p>
          <Link
            to="/discover"
            className="mt-4 inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
          >
            Browse scholarships
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {apps.map((app) => {
            const noteVal = editingNotes[app.id] ?? app.notes ?? "";
            return (
              <div
                key={app.id}
                className="rounded-xl border border-slate-200 bg-white p-5 space-y-3"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <span className="inline-block rounded bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                      User-maintained status
                    </span>
                    <Link
                      to={`/scholarships/${app.scholarship_id}`}
                      className="mt-1 block text-base font-bold text-slate-900 hover:text-blue-700"
                    >
                      {app.scholarship_name}
                    </Link>
                    <p className="text-xs text-slate-500">
                      {app.provider} • Official deadline: {formatDate(app.application_deadline)} •
                      Updated: {formatDateTime(app.updated_by_user_at)}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <select
                      aria-label={`Status for ${app.scholarship_name}`}
                      value={app.status}
                      onChange={(e) =>
                        patchMutation.mutate({
                          id: app.id,
                          status: e.target.value as ApplicationProgressStatus,
                        })
                      }
                      className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium"
                    >
                      {TRACKING_STATUS_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>

                    {app.official_application_url && (
                      <a
                        href={app.official_application_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
                      >
                        Apply Portal <ExternalLink className="h-3 w-3" />
                      </a>
                    )}

                    <button
                      type="button"
                      onClick={() => deleteMutation.mutate(app.id)}
                      className="rounded-lg border border-slate-200 p-1.5 text-slate-500 hover:bg-rose-50 hover:text-rose-700"
                      aria-label="Delete tracking item"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div className="flex gap-2">
                  <input
                    type="text"
                    value={noteVal}
                    onChange={(e) =>
                      setEditingNotes({ ...editingNotes, [app.id]: e.target.value })
                    }
                    placeholder="Personal notes (e.g., pending income certificate from Tahsildar)..."
                    className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => patchMutation.mutate({ id: app.id, notes: noteVal })}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    Save note
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
