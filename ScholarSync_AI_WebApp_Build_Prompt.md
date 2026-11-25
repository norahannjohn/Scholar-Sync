# AI Build Prompt: ScholarSync — Agentic AI Scholarship Discovery Web App

> **Instructions:** Give this entire prompt to your AI coding agent (for example, a coding assistant connected to your project/repository). The agent should build the application, not merely describe how it could be built. Work in small, testable phases and keep the app runnable throughout development.

---

## 1. Your role and mission

Act as a senior full-stack engineer, product designer, database architect, and applied-AI engineer. Build **ScholarSync**, a responsive web application for students in India to discover scholarships that may suit their academic and financial circumstances, understand eligibility requirements, and get trustworthy application guidance.

Your job is to inspect the current repository first. If it is empty, scaffold the project using the stack below. If code already exists, understand and preserve useful work rather than replacing it unnecessarily. Then implement the application end-to-end: frontend, backend, database models and migrations, core business logic, AI integration, tests, setup instructions, and a polished user experience.

Do not stop after generating a plan, wireframe, or static mockup. Build working features. Do not leave important buttons as decorative controls. When a third-party key or external service is unavailable, implement a clear, usable fallback and document exactly what needs configuration.

## 2. Product brief

### The problem

Students in India often need to search multiple central-government, state-government, and institutional portals to find scholarships. Eligibility rules can be complex, information is spread across different sources, and changing deadlines make suitable opportunities easy to miss.

### Target users

School, college, and university students in India who are looking for merit-based, income-based, or category-specific financial support, especially students who are unsure where to search or how to apply.

### The solution

A student creates an account, enters only the profile details needed for preliminary matching, and receives a ranked list of scholarships that may fit. ScholarSync explains the eligibility result, shows supporting information from official sources, highlights deadlines and official application links, and provides an AI assistant with a personalized application checklist.

### Product promise

**Find relevant opportunities, understand why they may fit, and know what to do next — with official-source evidence.**

### MVP success target

The product should be testable with 5–10 students. The target is that **at least 8 out of 10 test users find one relevant opportunity within 3 minutes**, and every displayed scholarship recommendation has a source reference or is explicitly marked as sample/demo content.

## 3. Non-negotiable product principles

1. **Official-source-first:** Prefer official government, institution, or scholarship-provider websites and official guideline documents. Show the source URL and the date the information was last checked and last verified, whenever known.
2. **Never invent scholarship facts:** Do not fabricate schemes, eligibility criteria, award amounts, dates, application links, or official endorsements. Seed data must be clearly labelled `DEMO / SAMPLE — NOT VERIFIED` and must never be presented as a real current opportunity.
3. **Eligibility must be deterministic:** A Python rules engine, not the language model, decides `PASS`, `FAIL`, or `UNKNOWN` for each criterion and for the overall preliminary match. Unknown or missing information must never silently become a pass.
4. **AI is an explainer and coordinator, not the authority:** The LLM can call tools, retrieve official passages, summarize, rank, and explain. It cannot override the rules engine or claim official approval.
5. **Privacy by design:** Do not ask for or store Aadhaar numbers, bank details, passwords for scholarship portals, or certificate scans. Do not require uploads of income, caste/community, birth, identity, or other sensitive certificates just to discover scholarships. Collect only fields needed for matching, explain why they are requested, and let users skip optional fields.
6. **Clear uncertainty:** Distinguish `eligible based on available details`, `not eligible based on a known failed rule`, and `cannot determine yet`. State that matches are preliminary and that the provider's official rules and verification process are authoritative.
7. **No unauthorized automation:** Do not bypass logins, CAPTCHAs, access controls, rate limits, or website restrictions. Only use public sources where collection is permitted, and respect provider terms and applicable policies. Never submit a student's application on their behalf.
8. **Useful without AI keys:** Core profile, search, filtering, scholarship details, eligibility evaluation, saving, and tracking must work without a Gemini API key. AI features should show a helpful setup/fallback message rather than crash.
9. **Accessible and responsive:** Build for mobile, tablet, and desktop. Use clear language, keyboard-accessible controls, readable contrast, useful empty states, loading states, and error messages.

## 4. Required technology stack

Use this stack unless the existing repository has a strong, documented reason to retain an equivalent:

### Frontend
- React with Vite
- TypeScript
- Tailwind CSS
- React Router for navigation
- TanStack Query (or an equivalent well-supported approach) for server state and API caching
- A small, consistent component system; use accessible components and avoid excessive dependencies

### Backend
- Python with FastAPI
- Pydantic schemas
- SQLAlchemy 2.x ORM
- Alembic database migrations
- PostgreSQL as the primary database
- Secure password hashing (Argon2id preferred) and JWT or secure session-based authentication

### AI and retrieval
- Gemini API for conversational assistance and tool/function calling
- A retrieval layer for official scholarship guidelines and notices
- ChromaDB for local/dev vector retrieval, or a clearly documented alternative if simpler for the chosen deployment
- PyMuPDF for PDF text extraction

### Data collection and scheduled checks
- `requests` and BeautifulSoup for permitted public HTML sources
- Playwright only when a permitted public page requires JavaScript rendering
- APScheduler for an initial, single-instance scheduled task runner
- Keep collectors modular so a more scalable queue can be added later

### Development and operations
- Docker Compose for local PostgreSQL (and any required local service)
- `.env.example` with variable names and safe placeholders only
- Clear README with setup, migrations, run commands, tests, and deployment notes

Do not introduce microservices, Kubernetes, Redis, Celery, or complex cloud infrastructure for the MVP unless the repository already requires them.

## 5. Core MVP features

Build these three features as the first usable release. Supporting pages and infrastructure listed later should serve these features rather than expand the scope unnecessarily.

### Feature A — Student profile and personalized discovery

Create registration, login, logout, and a student profile flow. Explain why each profile field is requested. Support editing the profile later.

Suggested profile fields (make optional where possible):
- Full name or display name
- State/Union Territory of residence
- Current education level (school / undergraduate / postgraduate / doctoral / other)
- Course or field of study
- Current year/grade
- Institution name and institution type
- Academic performance (percentage, CGPA, or marks) with a clearly stored grading type and scale
- Approximate annual family income range, only if needed for matching
- Category/community eligibility field only if the user chooses to provide it and only where relevant to a scheme
- Gender field only if a scheme explicitly uses it; provide a prefer-not-to-say option
- Other narrowly scoped criteria only when supported by actual scholarship rules

Do not infer a user's category, gender, disability status, religion, or income. Do not force sensitive optional fields during registration. Do not collect documents for profile completion.

The discovery page must support:
- Search by scholarship name, provider, course, or keyword
- Filters for education level, state, scholarship type, deadline/status, and provider, where data exists
- Sorting by relevance, deadline, or recently verified
- Clear cards with provider, award amount if verified, deadline if known, eligibility status, and source freshness
- A concise reason for a match and a link to the detail page
- Empty states explaining how profile completion or filters affect results

### Feature B — Transparent eligibility evaluation

Implement a separate Python eligibility module. It must not depend on Gemini.

For every scholarship criterion, return:
- `PASS`: user data is present and satisfies the rule
- `FAIL`: user data is present and does not satisfy the rule
- `UNKNOWN`: required user data or reliable rule data is missing/ambiguous

For each result, include:
- Criterion name
- Human-readable rule description
- Result (`PASS`, `FAIL`, or `UNKNOWN`)
- The relevant profile value, where appropriate and safe to display
- Explanation
- Source reference or guideline passage supporting the rule, if available

Overall status:
- `NOT_ELIGIBLE` when at least one mandatory criterion is `FAIL`
- `NEEDS_MORE_INFORMATION` when no mandatory criterion fails and one or more required criteria are `UNKNOWN`
- `POTENTIAL_MATCH` when all required criteria pass

Do not use a numeric percentage as a substitute for rule-based eligibility. If ranking is used, rank only among the scholarships that have not been ruled out, and explain that ranking is a relevance ordering, not an eligibility guarantee.

Store scholarship criteria in structured data, not arbitrary executable code. Support common operators such as equality, inclusion, minimum, maximum, range, and boolean conditions. Validate rule definitions with Pydantic and reject malformed or unsupported rules safely. Add unit tests for boundaries, missing values, different grading scales, and combinations of pass/fail/unknown results.

### Feature C — Official evidence, AI guidance, checklist, and saved matches

Each scholarship detail page should include:
- Scholarship name and provider
- Brief description
- Award amount or benefits, only when verified
- Eligibility requirements in readable language
- Application opening and closing dates, with timezone/context where relevant
- Current status (`OPEN`, `UPCOMING`, `CLOSED`, `UNKNOWN`)
- Official information page and official application link as separate fields when available
- Source last-checked time and last-verified time
- Eligibility breakdown for the signed-in student
- Evidence snippets linked to the source guideline or webpage
- A clear disclaimer that the student must confirm details on the provider's official portal

AI assistant behavior:
- Answer questions about scholarships using retrieved official material and database records.
- Explain why a scholarship matched or did not match, using the deterministic eligibility output.
- Identify missing information and ask only for the minimum necessary clarification.
- Create a personalized document checklist based on the official guideline. Mark checklist items as `required`, `conditional`, or `confirm_with_provider` where the source does not make the requirement clear.
- Give a numbered, understandable application walkthrough based on official instructions.
- Link or cite the specific official page/document passages used. Never invent a source citation.
- If retrieved material is insufficient or contradictory, say so and direct the student to the official provider source.
- Never claim the AI submitted an application, verified a certificate, contacted a provider, or obtained an approval.

Saved matches:
- Let the student save and unsave scholarships.
- Let the student view a saved-scholarship list.
- Let the student track their own progress with simple statuses such as `INTERESTED`, `PREPARING`, `READY_TO_APPLY`, `SUBMITTED`, `AWAITING_UPDATE`, `AWARDED`, and `NOT_SELECTED`.
- Clearly label these as user-maintained statuses, not statuses retrieved from the official portal.

## 6. Scholarship data and source intelligence

Create a normalized scholarship data model. At minimum, store:
- Stable scholarship ID
- Name, provider, provider type, description
- Applicable states/regions
- Education levels, courses, institution constraints
- Benefits/amount and benefit type
- Structured eligibility rules
- Application start date and deadline (nullable)
- Status and status reason
- Official information URL and official application URL
- Source type and source URL
- Source publication/effective date if known
- `last_checked_at`
- `last_verified_at`
- Verification state (`VERIFIED`, `NEEDS_REVIEW`, `UNVERIFIED`, `STALE`)
- Current version number
- Created/updated timestamps

Create a `scholarship_versions` history table. When a meaningful field changes, preserve the previous version and record what changed, when it changed, the source, and whether the new value has been reviewed. Never silently overwrite historical facts.

Create a source registry containing the source name, owner/provider, URL, source type, permitted collection method, checking interval, active flag, last successful check, and notes about restrictions or access requirements.

### Source collection approach

Implement a modular collector interface with separate adapters for:
- Manually entered or admin-verified scholarship information
- Public structured/API data where a provider actually offers authorized access
- Permitted public HTML pages
- Official PDF guidelines and circulars

Do not assume every government portal exposes a public API. Do not hardcode an invented API endpoint. Do not treat an old or undocumented API specification as proof of current public access.

For the initial MVP, prioritize a reliable source registry and an admin/manual verification workflow. Add a small working collector example against a clearly labelled configurable public source only when permitted. Keep the scraper generic and configurable; do not build a brittle scraper for every portal before the core product works.

### Change detection and freshness

Implement a scheduled source-check workflow that:
1. Fetches a permitted source with sensible timeouts and rate limits.
2. Stores a check log and fetch timestamp.
3. Computes a content hash as an initial change signal.
4. Extracts structured fields where an adapter supports them.
5. Compares actual fields such as deadline, amount, eligibility, application status, and guideline version.
6. Marks potentially important changes `NEEDS_REVIEW` until validated when extraction is uncertain.
7. Creates a new version only when a meaningful change is confirmed or approved.
8. Updates `last_checked_at` even when no change is found.
9. Updates `last_verified_at` only after the information has actually been verified against the source.

A changed page hash alone is not proof that a scholarship fact changed; page layout, analytics, or formatting may also change. Do not automatically publish uncertain extracted values as verified.

Show freshness honestly in the UI. If a source cannot be reached or is old, show `STALE` or `UNVERIFIED`, not a false claim of live accuracy. Describe the product as periodically updated, not instantaneously synchronized.

When a confirmed deadline or eligibility change affects saved or potentially matched students, create an in-app notification. Keep email/SMS optional and out of the MVP unless configured and consented to.

## 7. Database design

Create SQLAlchemy models and Alembic migrations for at least:

- `users`: authentication identity, normalized email, password hash, timestamps, active state
- `student_profiles`: one-to-one student profile, minimal matching fields, consent/preference fields as needed
- `scholarships`: current normalized scholarship record
- `scholarship_versions`: immutable historical snapshots or field-change records
- `scholarship_sources`: source registry
- `source_check_logs`: fetch/check outcomes, timestamps, hashes, errors
- `saved_scholarships`: user-to-scholarship relation
- `student_applications`: user-maintained tracking status and notes; do not imply official portal integration
- `notifications`: in-app notifications and read state
- `guideline_documents`: document metadata, source, version, extraction status
- `guideline_chunks`: extracted text chunks and citation metadata, if using relational storage for RAG references

Add indexes for common discovery filters and foreign keys. Use UTC timestamps in storage; convert to local display time in the UI. Use migrations rather than relying on automatic table creation in production.

## 8. Backend API requirements

Use versioned REST endpoints under `/api/v1`. Provide typed request/response schemas and consistent error responses. Suggested endpoint groups:

- `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`
- `/profile` GET/PUT
- `/scholarships` GET with search, filters, pagination, and sort
- `/scholarships/{id}` GET
- `/scholarships/{id}/eligibility` GET or POST for the current user's evaluation
- `/saved` GET/POST/DELETE
- `/applications` GET/POST/PATCH/DELETE
- `/notifications` GET and mark-read endpoint
- `/assistant/chat` POST for a chat turn
- `/assistant/checklist/{scholarship_id}` POST or GET
- Admin-only source/scholarship management endpoints for creating, editing, verifying, and reviewing changes
- Health endpoint such as `/health`

Enforce authorization on every user-owned resource. A user must never be able to read or edit another user's profile, saved list, tracking record, or notifications by changing an ID.

Add pagination and validation. Do not expose password hashes or internal secrets in API responses or logs.

## 9. AI agent and RAG architecture

Implement the agent as a controlled coordinator around explicit backend tools. Do not let the LLM run arbitrary SQL, Python, shell commands, or unrestricted web requests.

Suggested tools:
- `search_scholarships(query, filters)` — searches the application's scholarship database
- `get_scholarship_details(scholarship_id)` — returns the current record and source freshness
- `evaluate_eligibility(student_id, scholarship_id)` — calls the deterministic Python rules engine
- `retrieve_guideline_evidence(scholarship_id, question)` — retrieves relevant official document chunks with source metadata
- `get_application_checklist(scholarship_id, student_profile)` — assembles checklist items from verified source data
- `save_scholarship(user_id, scholarship_id)` — only for the authenticated user
- `update_tracking_status(user_id, scholarship_id, status)` — only for the authenticated user and only after explicit user intent

Agent workflow for a question such as “Which scholarships can I apply for?”:
1. Load the authenticated user's profile and consented optional fields.
2. Search the current scholarship database.
3. Evaluate each candidate with the deterministic rules engine.
4. Exclude mandatory `FAIL` matches from potential matches and identify `UNKNOWN` cases needing more information.
5. Retrieve official guideline evidence for the strongest candidates.
6. Consider deadline/status and source freshness.
7. Return a ranked, concise list with eligibility breakdown, missing information, evidence links, and next steps.

RAG requirements:
- Ingest only official/authorized documents and pages.
- Preserve metadata for every chunk: scholarship ID, document title, provider, source URL, page number if available, document version, retrieval timestamp, and verification status.
- Chunk PDFs and HTML into useful passages; avoid embedding navigation menus and irrelevant page furniture where possible.
- Return source metadata together with retrieved text so the UI can show citations.
- Re-index changed guidelines while preserving document/version history.
- Never fabricate page numbers or citations.

### AI prompt behavior

The assistant's system instructions should enforce the principles below:
- You are ScholarSync's scholarship information guide, not a government officer or scholarship provider.
- Use tool results and retrieved official evidence for factual scholarship claims.
- Do not guess deadlines, award amounts, eligibility rules, required documents, or portal status.
- Never override eligibility engine output.
- Explicitly identify unknowns, stale sources, conflicting evidence, and unverified sample data.
- Explain recommendations in simple, supportive language suitable for students.
- Do not request Aadhaar, bank account information, passwords, or certificate uploads.
- Do not claim to have submitted applications or contacted providers.
- Always distinguish general guidance from provider-specific instructions.

If Gemini is not configured, provide a basic non-LLM experience: eligibility explanation generated from rule results, a source-linked checklist from stored data, and a clear message that conversational AI is not configured.

## 10. Frontend pages and user experience

Build a polished, coherent visual identity for ScholarSync. The UI should feel trustworthy, student-friendly, modern, and calm — not like a generic admin dashboard. Use a restrained color palette, strong typography, clear hierarchy, consistent spacing, and reusable components. Avoid visual clutter, fake statistics, fake testimonials, and decorative charts with invented data.

Required routes/pages:
1. **Landing page:** clear value proposition, how it works, key features, privacy-first note, and calls to action.
2. **Register / Login:** clear validation and accessible forms.
3. **Onboarding / Profile:** progressive form with optional fields and explanations. Show progress and allow users to skip optional sensitive fields.
4. **Student dashboard:** relevant scholarship matches, saved items, upcoming deadlines from verified data, and next steps. Do not show fabricated totals.
5. **Discover scholarships:** search, filters, sorting, pagination, and useful empty/loading/error states.
6. **Scholarship detail:** provider, benefits, criteria, eligibility breakdown, evidence and source freshness, official links, save action, checklist, and tracking action.
7. **AI assistant:** chat UI with cited evidence, clear unknowns, and graceful no-key fallback.
8. **Saved scholarships:** saved list with source freshness and current eligibility snapshot.
9. **Application tracker:** user-maintained progress statuses and notes.
10. **Profile/settings:** edit profile, account controls, and privacy information.
11. **Admin area:** protected source registry, scholarship editing, verification review, source-check logs, and change history. Keep admin functionality minimal but working.

Use clear labels such as “Potential match”, “Not eligible based on the information entered”, and “More information needed”. Avoid presenting PASS/FAIL/UNKNOWN codes without human-readable explanation.

## 11. Security, privacy, and responsible handling

Implement at least:
- Password hashing; never store plaintext passwords.
- Secure authentication cookies or carefully configured tokens; document the chosen approach.
- HTTPS assumption for production and secure cookie settings in production.
- CORS restricted to configured frontend origins.
- Server-side input validation and output encoding where relevant.
- Rate limiting on authentication and AI endpoints where practical.
- Authorization checks on all private records and admin endpoints.
- Secrets only in environment variables; never commit API keys.
- Safe error messages and structured logs without sensitive profile details.
- User ability to edit or delete their profile and account, with a clear data deletion path.
- Minimal collection and retention of personal data.
- No certificate or identity-document upload feature in the MVP.

Include a privacy page or concise privacy section that explains which fields are collected, why they are used, that matching is preliminary, and that users apply through official provider portals.

## 12. Testing and quality requirements

Add tests for:
- Registration/login and protected endpoints
- User data isolation and admin authorization
- Profile validation and optional fields
- Eligibility `PASS`, `FAIL`, and `UNKNOWN` behavior
- Eligibility boundaries (income caps, age limits, grades, dates)
- Missing or ambiguous scholarship rules
- Search, filter, sort, and pagination behavior
- Saved scholarships and user-maintained application tracking
- Source check failures and stale-source handling
- Version creation and review of detected changes
- AI no-key fallback and tool error handling

Add at least one end-to-end test of the main student journey:
register → complete profile → discover scholarships → open detail → view eligibility explanation → save scholarship → update tracking status.

Use realistic test fixtures, but clearly mark them as test fixtures. Do not insert sample fixtures into production data by default.

Before declaring a phase complete, run formatting/linting and tests. Fix errors rather than merely listing them.

## 13. Suggested project organization

Use a clear structure similar to this (adapt it to the repository if needed):

```text
scholarsync/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── profile/
│   │   │   ├── scholarships/
│   │   │   ├── eligibility/
│   │   │   ├── assistant/
│   │   │   ├── saved/
│   │   │   └── tracking/
│   │   ├── lib/
│   │   └── types/
│   └── ...
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── eligibility/
│   │   ├── agent/
│   │   ├── rag/
│   │   ├── collectors/
│   │   ├── monitoring/
│   │   ├── notifications/
│   │   └── db/
│   ├── alembic/
│   └── tests/
├── docker-compose.yml
├── .env.example
├── README.md
└── ...
```

Keep modules focused. Avoid putting all backend logic in one file or all frontend UI in one component.

## 14. Phased implementation order

Work in these phases. Keep the application runnable after each phase and do not skip ahead to advanced AI features before the core product works.

### Phase 0 — Inspect and plan
- Inspect repository, tooling, and existing code.
- Create a concise implementation checklist and proposed file structure.
- Identify any missing external credentials.
- Then begin implementation; do not stop after the plan.

### Phase 1 — Working foundation
- Scaffold frontend and FastAPI backend.
- Configure environment variables and Docker Compose PostgreSQL.
- Implement health check, database connection, SQLAlchemy models, and Alembic migrations.
- Build the design system, app shell, navigation, landing page, and responsive layouts.

### Phase 2 — Authentication and profile
- Implement secure registration/login/logout/current-user flow.
- Implement profile creation, editing, validation, and onboarding.
- Enforce user data isolation.

### Phase 3 — Scholarship catalogue and eligibility engine
- Implement scholarship CRUD for authorized admins.
- Implement discovery search, filters, sorting, pagination, and detail pages.
- Implement structured rules and deterministic `PASS` / `FAIL` / `UNKNOWN` evaluation.
- Add unit tests before connecting the LLM.

### Phase 4 — Saved items and tracking
- Implement saved scholarships, user-maintained application statuses, notifications UI, and dashboard summaries.

### Phase 5 — Official-source evidence and RAG
- Implement source registry, document metadata, PDF extraction, chunking, retrieval, and citation rendering.
- Ensure every fact shown in the UI includes its source state and freshness where available.

### Phase 6 — Gemini assistant and tools
- Add Gemini configuration and controlled tool/function calling.
- Implement evidence-grounded explanations, checklists, and application walkthroughs.
- Add no-key and failure fallbacks.

### Phase 7 — Change monitoring and admin review
- Implement permitted collectors, source check logs, content hash detection, structured comparison, version history, review flow, and scheduled checks.
- Add in-app notifications for confirmed changes affecting saved/matched users.

### Phase 8 — Final verification and handoff
- Run backend and frontend tests, linting, and type checks.
- Run the end-to-end student journey.
- Fix broken flows, responsive issues, and console/API errors.
- Update the README and `.env.example`.
- Provide a concise handoff summary with what works, how to run it, required configuration, tests run, and known limitations.

## 15. Environment variables

Create `.env.example` with placeholders for variables such as:

```env
APP_ENV=development
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/scholarsync
FRONTEND_ORIGIN=http://localhost:5173
GEMINI_API_KEY=
GEMINI_MODEL=
CHROMA_PERSIST_DIRECTORY=./storage/chroma
SCHEDULER_ENABLED=false
ADMIN_EMAIL=
```

Adjust names to the implementation, validate required configuration at startup, and never place real secrets in source control. Provide a safe way to create the first admin account; do not hardcode a public default admin password.

## 16. Definition of done

The MVP is complete only when all of the following are true:

- A student can register, log in, and manage a profile.
- The student can search and filter a scholarship catalogue.
- A scholarship detail page shows official-source information and freshness state.
- The eligibility engine produces explainable `PASS`, `FAIL`, and `UNKNOWN` results.
- The student can save scholarships and maintain their own application progress.
- The dashboard shows the student's matches and next steps without fabricated statistics.
- The AI assistant can use controlled tools and official evidence when configured, and degrades gracefully when it is not.
- The source registry and version/check history exist; uncertain changes are not silently published as verified.
- Authorization, privacy safeguards, and tests are in place.
- The project can be started locally by following the README.

## 17. Final instructions to the coding agent

- Make sensible implementation decisions without repeatedly asking the user questions. State assumptions in the README when necessary.
- Prioritize a complete, trustworthy MVP over an oversized feature list.
- Build real database-backed flows; do not use hardcoded frontend arrays as the production data source.
- Use clearly labelled demo fixtures only for development and tests.
- Do not fake live scholarship data, government integrations, emails, notifications, citations, or application submission.
- Do not let Gemini make eligibility decisions or invent missing facts.
- Keep the frontend and backend contracts aligned and typed.
- Run the app and tests, inspect errors, and fix them.
- When you finish, report: **(1)** features implemented, **(2)** exact setup/run commands, **(3)** environment variables and credentials still needed, **(4)** tests and checks run with results, and **(5)** remaining limitations or work that requires authorized external access.

**Now inspect the repository and start building ScholarSync.**
