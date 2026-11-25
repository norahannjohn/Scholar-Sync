import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../lib/api";
import { useAuth } from "../auth/AuthContext";
import type { StudentProfile } from "../../types/api";

export function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: profile } = useQuery<StudentProfile>({
    queryKey: ["profile"],
    queryFn: () => apiFetch<StudentProfile>("/profile"),
  });

  const deleteAccountMutation = useMutation({
    mutationFn: () => apiFetch("/auth/account", { method: "DELETE" }),
    onSuccess: async () => {
      await logout();
      navigate("/");
    },
  });

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Profile &amp; Account Settings</h1>
          <p className="mt-1 text-sm text-slate-600">{user?.email}</p>
        </div>
        <Link
          to="/onboarding"
          className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
        >
          Edit matching profile
        </Link>
      </div>

      {profile && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="text-lg font-bold text-slate-900">Current Stored Matching Fields</h2>
          <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs text-slate-500">Nationality</dt>
              <dd className="font-medium text-slate-900">{profile.nationality || "Not set"}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Study scope &amp; destinations</dt>
              <dd className="font-medium text-slate-900">
                {profile.study_scope_preference || "both"}
                {profile.preferred_destination_countries.length
                  ? ` (${profile.preferred_destination_countries.join(", ")})`
                  : ""}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Target university</dt>
              <dd className="font-medium text-slate-900">
                {profile.target_university || "Not specified"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">State / UT (India)</dt>
              <dd className="font-medium text-slate-900">{profile.state_ut || "Not set"}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Education level</dt>
              <dd className="font-medium text-slate-900">{profile.education_level || "Not set"}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Course / field</dt>
              <dd className="font-medium text-slate-900">{profile.course_field || "Not set"}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Institution type</dt>
              <dd className="font-medium text-slate-900">{profile.institution_type || "Not set"}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Academic score</dt>
              <dd className="font-medium text-slate-900">
                {profile.academic_score !== null
                  ? `${profile.academic_score} (${profile.grading_scale || "unspecified"})`
                  : "Not set"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Annual family income (INR)</dt>
              <dd className="font-medium text-slate-900">
                {profile.annual_family_income_inr !== null
                  ? `₹${profile.annual_family_income_inr.toLocaleString("en-IN")}`
                  : "Not provided"}
              </dd>
            </div>
          </dl>
        </div>
      )}

      <div className="rounded-2xl border border-rose-200 bg-white p-6">
        <h2 className="text-lg font-bold text-rose-900">Delete Account &amp; Personal Data</h2>
        <p className="mt-1 text-sm text-slate-600">
          Permanently deletes your user account, matching profile, saved scholarships, tracking
          notes, notifications, and chat history.
        </p>
        {!confirmDelete ? (
          <button
            type="button"
            onClick={() => setConfirmDelete(true)}
            className="mt-4 rounded-lg border border-rose-300 px-4 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50"
          >
            Delete my account
          </button>
        ) : (
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => deleteAccountMutation.mutate()}
              disabled={deleteAccountMutation.isPending}
              className="rounded-lg bg-rose-700 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-800"
            >
              {deleteAccountMutation.isPending ? "Deleting..." : "Confirm permanent deletion"}
            </button>
            <button
              type="button"
              onClick={() => setConfirmDelete(false)}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
