import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookmarkX, ExternalLink } from "lucide-react";
import { apiFetch } from "../../lib/api";
import { formatDate, formatDateTime } from "../../lib/format";
import { SchemeStatusBadge, VerificationBadge } from "../../components/StatusBadges";
import type { SavedScholarship } from "../../types/api";

export function SavedPage() {
  const queryClient = useQueryClient();
  const { data: saved, isLoading } = useQuery<SavedScholarship[]>({
    queryKey: ["saved"],
    queryFn: () => apiFetch<SavedScholarship[]>("/saved"),
  });

  const removeMutation = useMutation({
    mutationFn: (scholarshipId: string) =>
      apiFetch(`/saved/${scholarshipId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saved"] });
      queryClient.invalidateQueries({ queryKey: ["scholarships"] });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Saved Scholarships</h1>
        <p className="mt-1 text-sm text-slate-600">
          Your saved opportunities with current official source freshness and eligibility snapshot.
        </p>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
          Loading saved scholarships...
        </div>
      ) : !saved || saved.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center">
          <p className="text-base font-semibold text-slate-900">No saved scholarships yet</p>
          <p className="mt-1 text-sm text-slate-600">
            Browse verified opportunities on the Discover page and save ones you want to track.
          </p>
          <Link
            to="/discover"
            className="mt-4 inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
          >
            Discover scholarships
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {saved.map((item) => (
            <div
              key={item.id}
              className="flex flex-col justify-between gap-4 rounded-xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center"
            >
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <SchemeStatusBadge status={item.status} />
                  <VerificationBadge state={item.verification_state} />
                  {item.eligibility_label && (
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                      {item.eligibility_label}
                    </span>
                  )}
                </div>
                <Link
                  to={`/scholarships/${item.scholarship_id}`}
                  className="mt-2 block text-base font-bold text-slate-900 hover:text-blue-700"
                >
                  {item.scholarship_name}
                </Link>
                <p className="text-xs text-slate-500">
                  {item.provider} • Deadline: {formatDate(item.application_deadline)} • Last checked:{" "}
                  {formatDateTime(item.last_checked_at)}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={item.official_info_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Official <ExternalLink className="h-3.5 w-3.5" />
                </a>
                <button
                  type="button"
                  onClick={() => removeMutation.mutate(item.scholarship_id)}
                  className="inline-flex items-center gap-1 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-100"
                >
                  <BookmarkX className="h-3.5 w-3.5" />
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
