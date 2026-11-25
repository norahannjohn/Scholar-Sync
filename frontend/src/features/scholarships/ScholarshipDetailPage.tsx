import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bookmark,
  Bot,
  CheckCircle2,
  ExternalLink,
  FileText,
  Globe2,
  HelpCircle,
  XCircle,
} from "lucide-react";
import { apiFetch } from "../../lib/api";
import { formatDate, formatDateTime } from "../../lib/format";
import { useAuth } from "../auth/AuthContext";
import {
  EligibilityBadge,
  SchemeStatusBadge,
  VerificationBadge,
} from "../../components/StatusBadges";
import type { ChecklistResponse, ScholarshipDetail } from "../../types/api";

export function ScholarshipDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const { data: detail, isLoading, isError } = useQuery<ScholarshipDetail>({
    queryKey: ["scholarship", id],
    queryFn: () => apiFetch<ScholarshipDetail>(`/scholarships/${id}`),
    enabled: Boolean(id),
  });

  const { data: checklist } = useQuery<ChecklistResponse>({
    queryKey: ["checklist", id],
    queryFn: () => apiFetch<ChecklistResponse>(`/assistant/checklist/${id}`),
    enabled: Boolean(id) && Boolean(user),
  });

  const saveMutation = useMutation({
    mutationFn: () =>
      detail?.is_saved
        ? apiFetch(`/saved/${detail.id}`, { method: "DELETE" })
        : apiFetch("/saved", {
            method: "POST",
            body: JSON.stringify({ scholarship_id: detail?.id }),
          }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scholarship", id] });
      queryClient.invalidateQueries({ queryKey: ["saved"] });
    },
  });

  const trackMutation = useMutation({
    mutationFn: () =>
      apiFetch("/applications", {
        method: "POST",
        body: JSON.stringify({
          scholarship_id: detail?.id,
          status: "INTERESTED",
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });

  if (isLoading) {
    return <div className="py-12 text-center text-sm text-slate-500">Loading scholarship details...</div>;
  }
  if (isError || !detail) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800">
        Scholarship not found or unavailable.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <SchemeStatusBadge status={detail.status} />
            <VerificationBadge state={detail.verification_state} />
            <span className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-800">
              <Globe2 className="h-3 w-3" />
              {detail.destination_countries.join(", ")}
            </span>
            <EligibilityBadge eligibility={detail.eligibility} />
          </div>
          {user && (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <Bookmark className="h-4 w-4" />
                {detail.is_saved ? "Saved" : "Save"}
              </button>
              <button
                type="button"
                onClick={() => trackMutation.mutate()}
                disabled={trackMutation.isPending}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                {trackMutation.isSuccess ? "Added to Tracker" : "Track Progress"}
              </button>
              <Link
                to={`/assistant?scholarship=${detail.id}`}
                className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-800"
              >
                <Bot className="h-4 w-4" />
                Ask AI Guide
              </Link>
            </div>
          )}
        </div>

        <h1 className="mt-4 text-2xl font-bold text-slate-900">{detail.name}</h1>
        <p className="mt-1 text-sm font-medium text-slate-500">{detail.provider}</p>
        <p className="mt-3 text-sm leading-relaxed text-slate-700">{detail.description}</p>

        <div className="mt-6 grid gap-4 rounded-xl bg-slate-50 p-4 sm:grid-cols-3 lg:grid-cols-5 text-xs">
          <div>
            <span className="text-slate-400">Funding &amp; Benefits</span>
            <p className="mt-1 font-semibold text-slate-900">
              {detail.funding_type.replace(/_/g, " ")}
            </p>
            <p className="text-[11px] text-slate-600">
              {detail.benefit_amount_display || "Confirm on official portal"}
            </p>
          </div>
          <div>
            <span className="text-slate-400">Destination &amp; Nationality</span>
            <p className="mt-1 font-semibold text-slate-900">
              {detail.destination_countries.join(", ")}
            </p>
            <p className="text-[11px] text-slate-600">
              Eligible: {detail.eligible_nationalities.join(", ")}
            </p>
          </div>
          <div>
            <span className="text-slate-400">Host Universities / Courses</span>
            <p className="mt-1 font-semibold text-slate-900">
              {detail.target_universities.join(", ") || "Accredited institutions"}
            </p>
            <p className="text-[11px] text-slate-600">
              Levels: {detail.education_levels.join(", ")}
            </p>
          </div>
          <div>
            <span className="text-slate-400">Opening / Closing</span>
            <p className="mt-1 font-semibold text-slate-900">
              {formatDate(detail.application_start_date)} → {formatDate(detail.application_deadline)}
            </p>
            <p className="text-[11px] text-slate-500">{detail.deadline_timezone}</p>
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-slate-400">Source freshness</span>
            <p className="font-semibold text-slate-900">
              Checked: {formatDateTime(detail.last_checked_at)}
            </p>
            <a
              href={detail.official_info_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 font-semibold text-blue-700 hover:underline"
            >
              Official info page <ExternalLink className="h-3.5 w-3.5" />
            </a>
            {detail.official_application_url && (
              <a
                href={detail.official_application_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 font-semibold text-emerald-700 hover:underline"
              >
                Official portal <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </div>
        </div>

        <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs text-slate-600">
          <strong>Disclaimer:</strong> Eligibility evaluations are preliminary. Always confirm final
          rules, dates, and required documents directly on the provider&apos;s official portal before
          applying.
        </p>
      </div>

      {/* Deterministic Eligibility Breakdown */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-bold text-slate-900">Deterministic Eligibility Breakdown</h2>
        {!detail.eligibility ? (
          <p className="mt-2 text-sm text-slate-600">
            <Link to="/auth" className="font-semibold text-blue-700 hover:underline">
              Sign in
            </Link>{" "}
            and complete your student profile to see rule-by-rule PASS / FAIL / UNKNOWN results.
          </p>
        ) : (
          <>
            <p className="mt-1 text-sm text-slate-600">{detail.eligibility.summary}</p>
            <div className="mt-4 space-y-3">
              {detail.eligibility.criteria_results.map((c) => (
                <div key={c.key} className="rounded-xl border border-slate-200 p-4 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 font-semibold text-slate-900">
                      {c.result === "PASS" && <CheckCircle2 className="h-4 w-4 text-emerald-600" />}
                      {c.result === "FAIL" && <XCircle className="h-4 w-4 text-rose-600" />}
                      {c.result === "UNKNOWN" && <HelpCircle className="h-4 w-4 text-amber-600" />}
                      {c.criterion_name}
                    </div>
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                      {c.result === "PASS"
                        ? "Passed"
                        : c.result === "FAIL"
                        ? "Not met"
                        : "More info needed"}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">Rule: {c.rule_description}</p>
                  <p className="mt-1.5 text-slate-700">{c.explanation}</p>
                  {c.source_reference && (
                    <p className="mt-1 text-xs text-slate-500">Source: {c.source_reference}</p>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {/* Checklist & Application Walkthrough */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-bold text-slate-900">Document Checklist</h2>
          <div className="mt-4 space-y-3">
            {(checklist?.items ??
              detail.required_documents.map((d) => ({
                item: d.item,
                requirement_level: d.status,
                note: d.note,
              }))).map((doc, idx) => (
              <div key={idx} className="rounded-lg border border-slate-200 p-3 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-slate-900">{doc.item}</span>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">
                    {doc.requirement_level.replace(/_/g, " ")}
                  </span>
                </div>
                {doc.note && <p className="mt-1 text-xs text-slate-600">{doc.note}</p>}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-bold text-slate-900">Official Application Steps</h2>
          <ol className="mt-4 list-decimal space-y-2.5 pl-5 text-sm text-slate-700">
            {detail.application_steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </section>
      </div>

      {/* Official Evidence Snippets */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6">
        <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
          <FileText className="h-5 w-5 text-slate-700" />
          Official Source Evidence &amp; Extracted Passages
        </h2>
        {detail.evidence_snippets.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">
            No guideline PDF/HTML chunks indexed yet. An admin can run official source sync to
            index live official passages.
          </p>
        ) : (
          <div className="mt-4 space-y-3">
            {detail.evidence_snippets.map((ev) => (
              <div key={ev.chunk_id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="font-semibold text-slate-900">
                    {ev.document_title}
                    {ev.page_number ? ` • Page ${ev.page_number}` : ""}
                  </span>
                  <a
                    href={ev.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-700 hover:underline"
                  >
                    Official Source
                  </a>
                </div>
                <p className="mt-2 whitespace-pre-line text-xs leading-relaxed text-slate-700">
                  {ev.excerpt}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
