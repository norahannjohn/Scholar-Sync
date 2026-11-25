import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, Globe2, Lock, Sparkles } from "lucide-react";

export function LandingPage() {
  return (
    <div className="space-y-16 py-6">
      <section className="rounded-2xl border border-slate-200 bg-white px-6 py-12 shadow-xs sm:px-12 sm:py-16">
        <div className="max-w-3xl">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">
            India &amp; Study Abroad • Live Official Verification • Privacy First
          </span>
          <h1 className="mt-5 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
            Discover scholarships in India and abroad with live official proof.
          </h1>
          <p className="mt-5 text-base leading-relaxed text-slate-600 sm:text-lg">
            ScholarSync helps students in India find scholarships within India and international
            funding for studying abroad — checking destination country, university, nationality, and
            funding type with deterministic rules and live official-website verification.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to="/auth?mode=register"
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800"
            >
              Get started free
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to="/discover"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-50"
            >
              Browse verified schemes
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-800">
            <Globe2 className="h-5 w-5" />
          </div>
          <h2 className="mt-4 text-lg font-bold text-slate-900">1. India + Study Abroad</h2>
          <p className="mt-2 text-sm text-slate-600">
            Covers Indian statutory schemes (AICTE) alongside international scholarships open to
            Indians (UK, EU, France, Japan, US), filtered by country, university, and funding type.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-800">
            <Sparkles className="h-5 w-5" />
          </div>
          <h2 className="mt-4 text-lg font-bold text-slate-900">2. Active Discovery Agent</h2>
          <p className="mt-2 text-sm text-slate-600">
            Explain your goals in natural language — the agent searches the catalogue and live
            official portals, verifies reachable pages, and links official evidence.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-800">
            <CheckCircle2 className="h-5 w-5" />
          </div>
          <h2 className="mt-4 text-lg font-bold text-slate-900">3. Deterministic Rules</h2>
          <p className="mt-2 text-sm text-slate-600">
            Every criterion is evaluated in Python as Pass, Fail, or More Information Needed.
            Missing fields never silently pass.
          </p>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-slate-900 px-6 py-8 text-white sm:px-10">
        <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-teal-300">
              <Lock className="h-4 w-4" />
              Privacy by design
            </div>
            <h2 className="mt-2 text-xl font-bold">
              No Aadhaar numbers, no bank details, no certificate uploads required.
            </h2>
            <p className="mt-2 text-sm text-slate-300">
              Share only the academic and optional criteria needed for preliminary matching. You
              apply directly on the official scholarship provider portal.
            </p>
          </div>
          <Link
            to="/privacy"
            className="shrink-0 rounded-xl border border-slate-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800"
          >
            Read privacy details
          </Link>
        </div>
      </section>
    </div>
  );
}
