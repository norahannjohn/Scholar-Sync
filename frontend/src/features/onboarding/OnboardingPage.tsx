import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "../../lib/api";
import { INDIAN_STATES_AND_UTS } from "../../lib/format";
import type { StudentProfile } from "../../types/api";

const DESTINATION_OPTIONS = [
  "India",
  "United Kingdom",
  "United States",
  "Germany",
  "France",
  "European Union",
  "Japan",
  "Australia",
  "Canada",
];

export function OnboardingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const { data: profile, isLoading } = useQuery<StudentProfile>({
    queryKey: ["profile"],
    queryFn: () => apiFetch<StudentProfile>("/profile"),
  });

  const [form, setForm] = useState({
    display_name: "",
    nationality: "India",
    state_ut: "",
    study_scope_preference: "both",
    preferred_destination_countries: [] as string[],
    target_university: "",
    english_proficiency_test: "",
    work_experience_years: "",
    education_level: "",
    course_field: "",
    current_year_or_grade: "",
    institution_name: "",
    institution_type: "",
    grading_scale: "percentage",
    academic_score: "",
    class12_board_percentile: "",
    study_mode: "regular",
    annual_family_income_inr: "",
    gender: "prefer_not_to_say",
    category: "prefer_not_to_say",
    disability_percentage: "",
    is_single_girl_child: "",
    is_orphan_or_martyr_ward: "",
    receiving_other_scholarship: "",
    age_years: "",
    consent_matching: true,
  });

  useEffect(() => {
    if (!profile) return;
    setForm({
      display_name: profile.display_name ?? "",
      nationality: profile.nationality ?? "India",
      state_ut: profile.state_ut ?? "",
      study_scope_preference: profile.study_scope_preference ?? "both",
      preferred_destination_countries: profile.preferred_destination_countries ?? [],
      target_university: profile.target_university ?? "",
      english_proficiency_test: profile.english_proficiency_test ?? "",
      work_experience_years: profile.work_experience_years?.toString() ?? "",
      education_level: profile.education_level ?? "",
      course_field: profile.course_field ?? "",
      current_year_or_grade: profile.current_year_or_grade?.toString() ?? "",
      institution_name: profile.institution_name ?? "",
      institution_type: profile.institution_type ?? "",
      grading_scale: profile.grading_scale ?? "percentage",
      academic_score: profile.academic_score?.toString() ?? "",
      class12_board_percentile: profile.class12_board_percentile?.toString() ?? "",
      study_mode: profile.study_mode ?? "regular",
      annual_family_income_inr: profile.annual_family_income_inr?.toString() ?? "",
      gender: profile.gender ?? "prefer_not_to_say",
      category: profile.category ?? "prefer_not_to_say",
      disability_percentage: profile.disability_percentage?.toString() ?? "",
      is_single_girl_child:
        profile.is_single_girl_child === null ? "" : String(profile.is_single_girl_child),
      is_orphan_or_martyr_ward:
        profile.is_orphan_or_martyr_ward === null ? "" : String(profile.is_orphan_or_martyr_ward),
      receiving_other_scholarship:
        profile.receiving_other_scholarship === null
          ? ""
          : String(profile.receiving_other_scholarship),
      age_years: profile.age_years?.toString() ?? "",
      consent_matching: profile.consent_matching,
    });
  }, [profile]);

  const mutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiFetch<StudentProfile>("/profile", {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      queryClient.invalidateQueries({ queryKey: ["scholarships"] });
      navigate("/dashboard");
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : "Could not save profile.");
    },
  });

  const toggleCountry = (country: string) => {
    setForm((prev) => ({
      ...prev,
      preferred_destination_countries: prev.preferred_destination_countries.includes(country)
        ? prev.preferred_destination_countries.filter((c) => c !== country)
        : [...prev.preferred_destination_countries, country],
    }));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const parseBool = (v: string) => (v === "true" ? true : v === "false" ? false : null);
    mutation.mutate({
      display_name: form.display_name || null,
      nationality: form.nationality || null,
      state_ut: form.state_ut || null,
      study_scope_preference: form.study_scope_preference || null,
      preferred_destination_countries: form.preferred_destination_countries,
      target_university: form.target_university || null,
      english_proficiency_test: form.english_proficiency_test || null,
      work_experience_years: form.work_experience_years
        ? Number(form.work_experience_years)
        : null,
      education_level: form.education_level || null,
      course_field: form.course_field || null,
      current_year_or_grade: form.current_year_or_grade
        ? Number(form.current_year_or_grade)
        : null,
      institution_name: form.institution_name || null,
      institution_type: form.institution_type || null,
      grading_scale: form.academic_score ? form.grading_scale : null,
      academic_score: form.academic_score ? Number(form.academic_score) : null,
      class12_board_percentile: form.class12_board_percentile
        ? Number(form.class12_board_percentile)
        : null,
      study_mode: form.study_mode || null,
      annual_family_income_inr: form.annual_family_income_inr
        ? Number(form.annual_family_income_inr)
        : null,
      gender: form.gender || null,
      category: form.category || null,
      disability_percentage: form.disability_percentage
        ? Number(form.disability_percentage)
        : null,
      is_single_girl_child: parseBool(form.is_single_girl_child),
      is_orphan_or_martyr_ward: parseBool(form.is_orphan_or_martyr_ward),
      receiving_other_scholarship: parseBool(form.receiving_other_scholarship),
      age_years: form.age_years ? Number(form.age_years) : null,
      consent_matching: form.consent_matching,
    });
  };

  if (isLoading) {
    return <div className="py-12 text-center text-sm text-slate-500">Loading your profile...</div>;
  }

  return (
    <div className="mx-auto max-w-2xl py-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs sm:p-8">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Step {step} of 3
          </span>
          <button
            type="button"
            onClick={() => navigate("/dashboard")}
            className="text-xs font-medium text-slate-500 hover:text-slate-900"
          >
            Skip for now
          </button>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full bg-slate-900 transition-all"
            style={{ width: `${(step / 3) * 100}%` }}
          />
        </div>

        <h1 className="mt-5 text-2xl font-bold text-slate-900">
          Student Profile (India &amp; Study Abroad)
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Every field is optional. We explain why each detail is used and never ask for Aadhaar,
          bank numbers, or certificate uploads.
        </p>

        {error && (
          <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-800">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          {step === 1 && (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Nationality / Citizenship
                  </label>
                  <p className="text-xs text-slate-500">
                    Required by international schemes (e.g., Commonwealth, Rhodes India, Eiffel).
                  </p>
                  <input
                    type="text"
                    value={form.nationality}
                    onChange={(e) => setForm({ ...form, nationality: e.target.value })}
                    placeholder="e.g. India"
                    className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Where do you plan to study?
                  </label>
                  <p className="text-xs text-slate-500">
                    Helps prioritize domestic Indian vs study-abroad scholarships.
                  </p>
                  <select
                    value={form.study_scope_preference}
                    onChange={(e) => setForm({ ...form, study_scope_preference: e.target.value })}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="both">Both India &amp; Study Abroad</option>
                    <option value="india">Within India</option>
                    <option value="abroad">Study Abroad (International)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">
                  Preferred destination countries (optional)
                </label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {DESTINATION_OPTIONS.map((c) => {
                    const active = form.preferred_destination_countries.includes(c);
                    return (
                      <button
                        key={c}
                        type="button"
                        onClick={() => toggleCountry(c)}
                        className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                          active
                            ? "border-slate-900 bg-slate-900 text-white"
                            : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                        }`}
                      >
                        {c}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">
                  State / Union Territory of residence in India
                </label>
                <select
                  value={form.state_ut}
                  onChange={(e) => setForm({ ...form, state_ut: e.target.value })}
                  className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                >
                  <option value="">Select State / UT (optional)</option>
                  {INDIAN_STATES_AND_UTS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Current / Target education level
                  </label>
                  <select
                    value={form.education_level}
                    onChange={(e) => setForm({ ...form, education_level: e.target.value })}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="">Select level</option>
                    <option value="school">School (Classes 1–12)</option>
                    <option value="diploma">Diploma / Polytechnic</option>
                    <option value="undergraduate">Undergraduate (B.E./B.Tech/B.Sc/BBA/BCA)</option>
                    <option value="postgraduate">Postgraduate (Master&apos;s / M.Tech / M.Sc)</option>
                    <option value="doctoral">Doctoral / PhD / Post-Doc</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Current year / grade
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={12}
                    value={form.current_year_or_grade}
                    onChange={(e) => setForm({ ...form, current_year_or_grade: e.target.value })}
                    placeholder="e.g. 1"
                    className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Course or field of study
                  </label>
                  <input
                    type="text"
                    value={form.course_field}
                    onChange={(e) => setForm({ ...form, course_field: e.target.value })}
                    placeholder="e.g. Computer Science, Mechanical Engineering"
                    className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Target university (optional)
                  </label>
                  <input
                    type="text"
                    value={form.target_university}
                    onChange={(e) => setForm({ ...form, target_university: e.target.value })}
                    placeholder="e.g. University of Cambridge, Oxford, IIT"
                    className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Institution type (for India schemes)
                  </label>
                  <select
                    value={form.institution_type}
                    onChange={(e) => setForm({ ...form, institution_type: e.target.value })}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="">Select institution type</option>
                    <option value="aicte_approved">AICTE-Approved Technical Institution</option>
                    <option value="central_university">Central University / INI</option>
                    <option value="state_university">State University / College</option>
                    <option value="foreign_university">Foreign / International University</option>
                    <option value="government_school">Government / Aided School</option>
                    <option value="private_recognized">Recognized Private Institution</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">Study mode</label>
                  <select
                    value={form.study_mode}
                    onChange={(e) => setForm({ ...form, study_mode: e.target.value })}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="regular">Regular / Full-time</option>
                    <option value="distance">Distance / Online</option>
                    <option value="part_time">Part-time</option>
                  </select>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700">Grading scale</label>
                  <select
                    value={form.grading_scale}
                    onChange={(e) => setForm({ ...form, grading_scale: e.target.value })}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="percentage">Percentage (%)</option>
                    <option value="cgpa_10">CGPA (10-point scale)</option>
                    <option value="cgpa_4">CGPA (4-point scale)</option>
                    <option value="marks">Total marks</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">Academic score</label>
                  <input
                    type="number"
                    step="0.01"
                    value={form.academic_score}
                    onChange={(e) => setForm({ ...form, academic_score: e.target.value })}
                    placeholder="e.g. 84.5"
                    className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                All fields below are <strong>strictly optional</strong>. Skip any field you prefer
                not to share — matching rules that need them will show as &quot;More information
                needed&quot;.
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700">Age (years)</label>
                  <p className="text-xs text-slate-500">
                    Used for schemes with age limits (e.g., Eiffel Master&apos;s ≤ 29, PhD ≤ 35).
                  </p>
                  <input
                    type="number"
                    min={5}
                    max={80}
                    value={form.age_years}
                    onChange={(e) => setForm({ ...form, age_years: e.target.value })}
                    placeholder="Optional"
                    className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    English proficiency test (optional)
                  </label>
                  <input
                    type="text"
                    value={form.english_proficiency_test}
                    onChange={(e) =>
                      setForm({ ...form, english_proficiency_test: e.target.value })
                    }
                    placeholder="e.g. IELTS 7.5, TOEFL, Not taken yet"
                    className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Annual family income (INR)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={form.annual_family_income_inr}
                    onChange={(e) =>
                      setForm({ ...form, annual_family_income_inr: e.target.value })
                    }
                    placeholder="e.g. 450000"
                    className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">Gender (optional)</label>
                  <select
                    value={form.gender}
                    onChange={(e) => setForm({ ...form, gender: e.target.value })}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="prefer_not_to_say">Prefer not to say</option>
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="non_binary">Non-binary</option>
                  </select>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Category / community (optional)
                  </label>
                  <select
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="prefer_not_to_say">Prefer not to say</option>
                    <option value="general">General</option>
                    <option value="obc">OBC</option>
                    <option value="sc">SC</option>
                    <option value="st">ST</option>
                    <option value="ews">EWS</option>
                    <option value="minority">Minority</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Disability % (optional)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={form.disability_percentage}
                    onChange={(e) => setForm({ ...form, disability_percentage: e.target.value })}
                    placeholder="Leave blank if not applicable"
                    className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Orphan / COVID loss / Martyr ward? (optional)
                  </label>
                  <select
                    value={form.is_orphan_or_martyr_ward}
                    onChange={(e) =>
                      setForm({ ...form, is_orphan_or_martyr_ward: e.target.value })
                    }
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="">Prefer not to answer / Skip</option>
                    <option value="false">No</option>
                    <option value="true">Yes</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700">
                    Receiving another scholarship?
                  </label>
                  <select
                    value={form.receiving_other_scholarship}
                    onChange={(e) =>
                      setForm({ ...form, receiving_other_scholarship: e.target.value })
                    }
                    className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    <option value="">Skip</option>
                    <option value="false">No</option>
                    <option value="true">Yes</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between border-t border-slate-100 pt-4">
            {step > 1 ? (
              <button
                type="button"
                onClick={() => setStep(step - 1)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Back
              </button>
            ) : (
              <span />
            )}

            {step < 3 ? (
              <button
                type="button"
                onClick={() => setStep(step + 1)}
                className="rounded-lg bg-slate-900 px-5 py-2 text-sm font-semibold text-white hover:bg-slate-800"
              >
                Continue
              </button>
            ) : (
              <button
                type="submit"
                disabled={mutation.isPending}
                className="rounded-lg bg-slate-900 px-5 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
              >
                {mutation.isPending ? "Saving..." : "Save profile & view matches"}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
