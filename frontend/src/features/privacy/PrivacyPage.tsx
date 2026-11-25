export function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 rounded-2xl border border-slate-200 bg-white p-6 sm:p-10">
      <h1 className="text-2xl font-bold text-slate-900">Privacy, Data Minimization &amp; Trust</h1>
      <p className="text-sm leading-relaxed text-slate-700">
        ScholarSync is designed around privacy by default. We collect only the minimum student
        details required to run deterministic scholarship eligibility checks.
      </p>

      <div className="space-y-4 text-sm text-slate-700">
        <section>
          <h2 className="font-bold text-slate-900">What we NEVER ask for or store</h2>
          <ul className="mt-1.5 list-disc space-y-1 pl-5">
            <li>Aadhaar numbers or government identity numbers</li>
            <li>Bank account numbers, IFSC codes, or financial documents</li>
            <li>Passwords for NSP, AICTE, state portals, or any third-party accounts</li>
            <li>Uploaded scans of income, caste, disability, or identity certificates</li>
          </ul>
        </section>

        <section>
          <h2 className="font-bold text-slate-900">Why optional profile fields exist</h2>
          <p className="mt-1">
            Fields like state, education level, course, income range, gender, and disability
            percentage map directly to explicit rules published in official scholarship guidelines.
            Optional sensitive fields can always be skipped or set to &quot;Prefer not to say&quot;.
          </p>
        </section>

        <section>
          <h2 className="font-bold text-slate-900">Preliminary matching &amp; official portals</h2>
          <p className="mt-1">
            ScholarSync performs preliminary eligibility evaluation and periodically checks public
            official portals and PDF guidelines. Final eligibility verification and application
            submission happen exclusively on the official scholarship provider&apos;s portal.
          </p>
        </section>
      </div>
    </div>
  );
}
