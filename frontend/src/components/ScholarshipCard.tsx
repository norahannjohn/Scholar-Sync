import { Link } from "react-router-dom";
import { Calendar, ExternalLink, Globe2 } from "lucide-react";
import { formatDate, formatDateTime } from "../lib/format";
import type { ScholarshipListItem } from "../types/api";
import { EligibilityBadge, SchemeStatusBadge, VerificationBadge } from "./StatusBadges";

export function ScholarshipCard({ item }: { item: ScholarshipListItem }) {
  const isAbroad = item.study_scope === "international_abroad";
  return (
    <article className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-xs transition hover:border-slate-300">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <SchemeStatusBadge status={item.status} />
            <VerificationBadge state={item.verification_state} />
            <span
              className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium ${
                isAbroad
                  ? "border-indigo-200 bg-indigo-50 text-indigo-800"
                  : "border-slate-200 bg-slate-50 text-slate-700"
              }`}
            >
              <Globe2 className="h-3 w-3" />
              {item.destination_countries.join(", ") || (isAbroad ? "Abroad" : "India")}
            </span>
          </div>
          <EligibilityBadge eligibility={item.eligibility} />
        </div>

        <h3 className="mt-3 text-base font-bold text-slate-900">
          <Link to={`/scholarships/${item.id}`} className="hover:text-blue-700">
            {item.name}
          </Link>
        </h3>
        <p className="mt-0.5 text-xs font-medium text-slate-500">
          {item.provider} • {item.funding_type.replace(/_/g, " ")}
        </p>
        <p className="mt-2 line-clamp-2 text-sm text-slate-600">{item.description}</p>

        {item.match_reason && (
          <div className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-700">
            <span className="font-semibold">Check summary: </span>
            {item.match_reason}
          </div>
        )}
      </div>

      <div className="mt-4 border-t border-slate-100 pt-3">
        <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
          <div>
            <span className="block text-[11px] text-slate-400">Benefits / Funding</span>
            <span className="font-medium text-slate-800">
              {item.benefit_amount_display || "See official guideline"}
            </span>
          </div>
          <div>
            <span className="block text-[11px] text-slate-400">Deadline</span>
            <span className="inline-flex items-center gap-1 font-medium text-slate-800">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              {formatDate(item.application_deadline)}
            </span>
          </div>
        </div>

        <div className="mt-3 flex items-center justify-between gap-2 text-xs">
          <span className="text-slate-400">
            Checked: {formatDateTime(item.last_checked_at)}
          </span>
          <div className="flex items-center gap-3">
            <a
              href={item.official_info_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 font-medium text-slate-600 hover:text-slate-900"
            >
              Official <ExternalLink className="h-3 w-3" />
            </a>
            <Link
              to={`/scholarships/${item.id}`}
              className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
            >
              View details
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}
