import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CalendarClock, CheckCircle2, Compass, Sparkles } from "lucide-react";
import { apiFetch } from "../../lib/api";
import { formatDate } from "../../lib/format";
import { ScholarshipCard } from "../../components/ScholarshipCard";
import type {
  NotificationItem,
  SavedScholarship,
  ScholarshipListResponse,
  StudentProfile,
} from "../../types/api";

export function DashboardPage() {
  const queryClient = useQueryClient();

  const { data: profile } = useQuery<StudentProfile>({
    queryKey: ["profile"],
    queryFn: () => apiFetch<StudentProfile>("/profile"),
  });

  const { data: catalog, isLoading: loadingCatalog } = useQuery<ScholarshipListResponse>({
    queryKey: ["scholarships", "dashboard"],
    queryFn: () => apiFetch<ScholarshipListResponse>("/scholarships?sort=relevance&page_size=20"),
  });

  const { data: saved } = useQuery<SavedScholarship[]>({
    queryKey: ["saved"],
    queryFn: () => apiFetch<SavedScholarship[]>("/saved"),
  });

  const { data: notifications } = useQuery<NotificationItem[]>({
    queryKey: ["notifications"],
    queryFn: () => apiFetch<NotificationItem[]>("/notifications"),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/notifications/${id}/read`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const items = catalog?.items ?? [];
  const potentialMatches = items.filter((s) => s.eligibility?.overall_status === "POTENTIAL_MATCH");
  const needsInfo = items.filter((s) => s.eligibility?.overall_status === "NEEDS_MORE_INFORMATION");
  const upcomingDeadlines = [...items]
    .filter((s) => s.application_deadline && s.status === "OPEN")
    .sort((a, b) =>
      (a.application_deadline || "").localeCompare(b.application_deadline || "")
    )
    .slice(0, 4);
  const unreadNotifs = (notifications ?? []).filter((n) => !n.is_read);

  return (
    <div className="space-y-8">
      <div className="flex flex-col justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Welcome{profile?.display_name ? `, ${profile.display_name}` : ""}
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Your dashboard reflects live verified records in the database and deterministic checks on
            your profile.
          </p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          <Link
            to="/onboarding"
            className="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Profile ({profile?.completeness_fields_filled ?? 0}/
            {profile?.completeness_total_core ?? 7} core)
          </Link>
          <Link
            to="/assistant"
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-sm font-semibold text-white hover:bg-slate-800"
          >
            <Sparkles className="h-4 w-4" />
            Ask AI Guide
          </Link>
        </div>
      </div>

      {/* Real DB-backed counts only */}
      <section className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium text-slate-500">Potential matches</p>
          <p className="mt-1 text-2xl font-bold text-emerald-700">{potentialMatches.length}</p>
          <p className="mt-1 text-xs text-slate-500">All mandatory stored criteria passed</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium text-slate-500">Need more profile details</p>
          <p className="mt-1 text-2xl font-bold text-amber-700">{needsInfo.length}</p>
          <p className="mt-1 text-xs text-slate-500">No mandatory rules failed yet</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium text-slate-500">Saved schemes</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{saved?.length ?? 0}</p>
          <p className="mt-1 text-xs text-slate-500">
            <Link to="/saved" className="text-blue-700 hover:underline">
              Open saved list
            </Link>
          </p>
        </div>
      </section>

      {unreadNotifs.length > 0 && (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-center gap-2 text-sm font-bold text-amber-900">
            <Bell className="h-4 w-4" />
            Official source updates ({unreadNotifs.length})
          </div>
          <div className="mt-3 space-y-2">
            {unreadNotifs.slice(0, 4).map((n) => (
              <div
                key={n.id}
                className="flex flex-col justify-between gap-2 rounded-lg bg-white p-3 text-sm sm:flex-row sm:items-center"
              >
                <div>
                  <p className="font-semibold text-slate-900">{n.title}</p>
                  <p className="text-xs text-slate-600">{n.message}</p>
                </div>
                <button
                  type="button"
                  onClick={() => markReadMutation.mutate(n.id)}
                  className="shrink-0 rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Mark read
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              Preliminary matches &amp; candidates
            </h2>
            <Link to="/discover" className="text-sm font-medium text-blue-700 hover:underline">
              Explore all ({catalog?.total ?? 0})
            </Link>
          </div>

          {loadingCatalog ? (
            <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
              Evaluating official schemes against your profile...
            </div>
          ) : items.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
              <Compass className="mx-auto h-8 w-8 text-slate-400" />
              <p className="mt-2 text-sm font-medium text-slate-800">
                No verified scholarships in catalog yet.
              </p>
              <p className="mt-1 text-xs text-slate-500">
                An administrator can add or sync official sources from the Admin panel.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {[...potentialMatches, ...needsInfo].slice(0, 4).map((item) => (
                <ScholarshipCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </section>

        <aside className="space-y-4">
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <CalendarClock className="h-5 w-5 text-slate-700" />
            Upcoming verified deadlines
          </h2>
          <div className="rounded-xl border border-slate-200 bg-white divide-y divide-slate-100">
            {upcomingDeadlines.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">
                No open deadlines recorded yet.
              </p>
            ) : (
              upcomingDeadlines.map((s) => (
                <Link
                  key={s.id}
                  to={`/scholarships/${s.id}`}
                  className="block p-4 hover:bg-slate-50"
                >
                  <p className="text-sm font-semibold text-slate-900">{s.name}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Closes: <strong className="text-slate-800">{formatDate(s.application_deadline)}</strong>
                  </p>
                </Link>
              ))
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
