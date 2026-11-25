import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { apiFetch } from "../../lib/api";
import { ScholarshipCard } from "../../components/ScholarshipCard";
import type { ScholarshipListResponse } from "../../types/api";

export function DiscoverPage() {
  const [q, setQ] = useState("");
  const [studyScope, setStudyScope] = useState("");
  const [destinationCountry, setDestinationCountry] = useState("");
  const [fundingType, setFundingType] = useState("");
  const [educationLevel, setEducationLevel] = useState("");
  const [stateUt, setStateUt] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState<"relevance" | "deadline" | "recently_verified">("relevance");
  const [page, setPage] = useState(1);

  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  if (studyScope) params.set("study_scope", studyScope);
  if (destinationCountry) params.set("destination_country", destinationCountry);
  if (fundingType) params.set("funding_type", fundingType);
  if (educationLevel) params.set("education_level", educationLevel);
  if (stateUt) params.set("state_ut", stateUt);
  if (status) params.set("status", status);
  params.set("sort", sort);
  params.set("page", String(page));
  params.set("page_size", "9");

  const { data, isLoading, isError } = useQuery<ScholarshipListResponse>({
    queryKey: ["scholarships", params.toString()],
    queryFn: () => apiFetch<ScholarshipListResponse>(`/scholarships?${params.toString()}`),
  });

  const filters = data?.available_filters;

  const resetFilters = () => {
    setQ("");
    setStudyScope("");
    setDestinationCountry("");
    setFundingType("");
    setEducationLevel("");
    setStateUt("");
    setStatus("");
    setSort("relevance");
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Discover Scholarships (India &amp; Study Abroad)
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Covers verified Indian government schemes and international scholarships open to Indian
          applicants, including destination country, university constraints, nationality, and funding
          type.
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs space-y-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="search"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
            placeholder="Search by scheme, university, country, or keyword (e.g., Pragati, Eiffel, Cambridge, Erasmus, MEXT)..."
            className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm focus:border-slate-900 focus:outline-none"
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <select
            aria-label="Filter by study scope"
            value={studyScope}
            onChange={(e) => {
              setStudyScope(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            <option value="">All locations (India &amp; Abroad)</option>
            <option value="india">Within India</option>
            <option value="international_abroad">Study Abroad (International)</option>
          </select>

          <select
            aria-label="Filter by destination country"
            value={destinationCountry}
            onChange={(e) => {
              setDestinationCountry(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            <option value="">All destination countries</option>
            {(filters?.destination_countries ?? []).map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter by funding type"
            value={fundingType}
            onChange={(e) => {
              setFundingType(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            <option value="">All funding types</option>
            {(filters?.funding_types ?? []).map((ft) => (
              <option key={ft} value={ft}>
                {ft.replace(/_/g, " ")}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter by education level"
            value={educationLevel}
            onChange={(e) => {
              setEducationLevel(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            <option value="">All education levels</option>
            {(filters?.education_levels ?? []).map((lv) => (
              <option key={lv} value={lv}>
                {lv}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter by Indian state"
            value={stateUt}
            onChange={(e) => {
              setStateUt(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            <option value="">All Indian States / UTs</option>
            {(filters?.states ?? []).map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>

          <select
            aria-label="Filter by status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="UPCOMING">UPCOMING</option>
            <option value="CLOSED">CLOSED</option>
            <option value="UNKNOWN">UNKNOWN</option>
          </select>

          <select
            aria-label="Sort scholarships"
            value={sort}
            onChange={(e) => setSort(e.target.value as typeof sort)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm sm:col-span-2"
          >
            <option value="relevance">Sort: Relevance (profile match first)</option>
            <option value="deadline">Sort: Soonest deadline</option>
            <option value="recently_verified">Sort: Recently verified</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
          Loading scholarships...
        </div>
      ) : isError ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800">
          Could not load scholarships. Please check your connection and try again.
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-10 text-center">
          <p className="text-base font-semibold text-slate-900">No matching scholarships found</p>
          <p className="mt-1 text-sm text-slate-600">
            Try clearing filters or ask the AI Scholarship-Discovery Agent to search live official
            websites for your country and course.
          </p>
          <button
            type="button"
            onClick={resetFilters}
            className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
          >
            Reset filters
          </button>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing {data.items.length} of {data.total} verified scheme(s)
            </span>
            <span>
              Page {data.page} of {data.total_pages}
            </span>
          </div>

          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {data.items.map((item) => (
              <ScholarshipCard key={item.id} item={item} />
            ))}
          </div>

          {data.total_pages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={page >= data.total_pages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
