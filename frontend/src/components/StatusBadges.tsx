import type { EligibilityEvaluation, ScholarshipListItem } from "../types/api";

export function EligibilityBadge({ eligibility }: { eligibility: EligibilityEvaluation | null }) {
  if (!eligibility) {
    return (
      <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
        Sign in to evaluate
      </span>
    );
  }
  const map = {
    POTENTIAL_MATCH:
      "border-emerald-200 bg-emerald-50 text-emerald-800",
    NEEDS_MORE_INFORMATION:
      "border-amber-200 bg-amber-50 text-amber-800",
    NOT_ELIGIBLE:
      "border-rose-200 bg-rose-50 text-rose-800",
  } as const;

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${map[eligibility.overall_status]}`}
    >
      {eligibility.overall_label}
    </span>
  );
}

export function VerificationBadge({ state }: { state: ScholarshipListItem["verification_state"] | string }) {
  const styles: Record<string, string> = {
    VERIFIED: "border-teal-200 bg-teal-50 text-teal-800",
    NEEDS_REVIEW: "border-amber-200 bg-amber-50 text-amber-800",
    STALE: "border-rose-200 bg-rose-50 text-rose-800",
    UNVERIFIED: "border-slate-200 bg-slate-100 text-slate-700",
  };
  const labels: Record<string, string> = {
    VERIFIED: "Official source verified",
    NEEDS_REVIEW: "Needs review",
    STALE: "Source stale",
    UNVERIFIED: "Unverified",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium ${styles[state] || styles.UNVERIFIED}`}
    >
      {labels[state] || state}
    </span>
  );
}

export function SchemeStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    OPEN: "bg-emerald-600 text-white",
    UPCOMING: "bg-sky-600 text-white",
    CLOSED: "bg-slate-500 text-white",
    UNKNOWN: "bg-slate-200 text-slate-800",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold tracking-wide ${styles[status] || styles.UNKNOWN}`}
    >
      {status}
    </span>
  );
}
