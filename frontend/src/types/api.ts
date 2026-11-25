export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface StudentProfile {
  id: string;
  user_id: string;
  display_name: string | null;
  nationality: string | null;
  state_ut: string | null;
  study_scope_preference: "india" | "abroad" | "both" | null;
  preferred_destination_countries: string[];
  target_university: string | null;
  preferred_funding_types: string[];
  english_proficiency_test: string | null;
  work_experience_years: number | null;
  education_level: string | null;
  course_field: string | null;
  current_year_or_grade: number | null;
  institution_name: string | null;
  institution_type: string | null;
  grading_scale: string | null;
  academic_score: number | null;
  class12_board_percentile: number | null;
  annual_family_income_inr: number | null;
  category: string | null;
  gender: string | null;
  disability_percentage: number | null;
  is_single_girl_child: boolean | null;
  is_orphan_or_martyr_ward: boolean | null;
  age_years: number | null;
  study_mode: string | null;
  receiving_other_scholarship: boolean | null;
  notes: string | null;
  consent_matching: boolean;
  completeness_fields_filled: number;
  completeness_total_core: number;
  updated_at: string;
}

export interface CriterionEvaluation {
  key: string;
  criterion_name: string;
  rule_description: string;
  result: "PASS" | "FAIL" | "UNKNOWN";
  mandatory: boolean;
  profile_value_display: string | null;
  explanation: string;
  source_reference: string | null;
}

export interface EligibilityEvaluation {
  overall_status: "POTENTIAL_MATCH" | "NOT_ELIGIBLE" | "NEEDS_MORE_INFORMATION";
  overall_label: string;
  summary: string;
  criteria_results: CriterionEvaluation[];
  passed_count: number;
  failed_count: number;
  unknown_count: number;
  missing_fields: string[];
  disclaimer: string;
}

export interface ScholarshipListItem {
  id: string;
  slug: string;
  name: string;
  provider: string;
  provider_type: string;
  scholarship_type: string;
  description: string;
  study_scope: "india" | "international_abroad" | "global" | string;
  destination_countries: string[];
  target_universities: string[];
  eligible_nationalities: string[];
  funding_type: string;
  applicable_states: string[];
  education_levels: string[];
  courses: string[];
  benefit_amount_display: string | null;
  benefit_amount_inr: number | null;
  benefit_type: string | null;
  application_start_date: string | null;
  application_deadline: string | null;
  deadline_timezone: string;
  status: "OPEN" | "UPCOMING" | "CLOSED" | "UNKNOWN";
  status_reason: string | null;
  official_info_url: string;
  official_application_url: string | null;
  source_type: string;
  source_url: string;
  last_checked_at: string | null;
  last_verified_at: string | null;
  verification_state: "VERIFIED" | "NEEDS_REVIEW" | "UNVERIFIED" | "STALE";
  current_version: number;
  eligibility: EligibilityEvaluation | null;
  match_reason: string | null;
  is_saved: boolean;
}

export interface EvidenceSnippet {
  chunk_id: string;
  document_title: string;
  source_url: string;
  page_number: number | null;
  section_heading: string | null;
  verification_status: string;
  retrieved_at: string;
  excerpt: string;
}

export interface ScholarshipVersion {
  id: string;
  version_number: number;
  changed_fields: Record<string, { old: unknown; new: unknown }>;
  change_source: string;
  source_url: string | null;
  reviewed: boolean;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface ScholarshipDetail extends ScholarshipListItem {
  institution_constraints: string | null;
  structured_rules: Record<string, unknown>;
  required_documents: Array<{ item: string; status: string; note?: string | null }>;
  application_steps: string[];
  source_publication_date: string | null;
  evidence_snippets: EvidenceSnippet[];
  recent_versions: ScholarshipVersion[];
}

export interface ScholarshipListResponse {
  items: ScholarshipListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  available_filters: {
    study_scopes: string[];
    destination_countries: string[];
    funding_types: string[];
    education_levels: string[];
    states: string[];
    scholarship_types: string[];
    statuses: string[];
    providers: string[];
  };
}

export interface SavedScholarship {
  id: string;
  scholarship_id: string;
  scholarship_name: string;
  provider: string;
  application_deadline: string | null;
  status: string;
  verification_state: string;
  last_checked_at: string | null;
  official_info_url: string;
  eligibility_status: string | null;
  eligibility_label: string | null;
  created_at: string;
}

export type ApplicationProgressStatus =
  | "INTERESTED"
  | "PREPARING"
  | "READY_TO_APPLY"
  | "SUBMITTED"
  | "AWAITING_UPDATE"
  | "AWARDED"
  | "NOT_SELECTED";

export interface StudentApplication {
  id: string;
  scholarship_id: string;
  scholarship_name: string;
  provider: string;
  application_deadline: string | null;
  scholarship_status: string;
  official_application_url: string | null;
  official_info_url: string;
  status: ApplicationProgressStatus;
  notes: string | null;
  updated_by_user_at: string;
  created_at: string;
  is_user_maintained: boolean;
}

export interface NotificationItem {
  id: string;
  scholarship_id: string | null;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  created_at: string;
}

export interface CitationItem {
  title: string;
  source_url: string;
  page_number: number | null;
  section_heading: string | null;
  verification_status: string;
  excerpt: string;
}

export interface LiveVerificationResult {
  title: string;
  url: string;
  http_status: number | null;
  verified_live: boolean;
  checked_at: string;
  excerpt: string | null;
  discovered_links: Array<{ label: string; url: string }>;
  error: string | null;
}

export interface AssistantChatResponse {
  reply: string;
  mode: string;
  citations: CitationItem[];
  live_verifications: LiveVerificationResult[];
  tool_calls_used: string[];
  gemini_configured: boolean;
  disclaimer: string;
}

export interface AssistantHistoryItem {
  id: string;
  scholarship_id: string | null;
  role: "user" | "assistant";
  content: string;
  citations: CitationItem[];
  mode: string;
  created_at: string;
}

export interface ChecklistResponse {
  scholarship_id: string;
  scholarship_name: string;
  official_info_url: string;
  official_application_url: string | null;
  verification_state: string;
  items: Array<{
    item: string;
    requirement_level: "required" | "conditional" | "confirm_with_provider";
    note: string | null;
    source_url: string | null;
  }>;
  application_steps: string[];
  disclaimer: string;
}

export interface SourceItem {
  id: string;
  name: string;
  owner_provider: string;
  url: string;
  source_type: string;
  collection_method: string;
  adapter_key: string | null;
  check_interval_hours: number;
  is_active: boolean;
  last_checked_at: string | null;
  last_successful_at: string | null;
  last_content_hash: string | null;
  last_error: string | null;
  access_notes: string | null;
  updated_at: string;
}

export interface SourceCheckLogItem {
  id: string;
  source_id: string;
  checked_at: string;
  http_status: number | null;
  success: boolean;
  content_hash: string | null;
  change_detected: boolean;
  auto_updated_count: number;
  summary: string | null;
  error_message: string | null;
}
