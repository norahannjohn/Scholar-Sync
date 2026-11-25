import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ExternalLink,
  Globe2,
  Send,
  Trash2,
  XCircle,
} from "lucide-react";
import { apiFetch, ApiError } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import type {
  AssistantChatResponse,
  AssistantHistoryItem,
  CitationItem,
  LiveVerificationResult,
} from "../../types/api";

function CitationList({ citations }: { citations: CitationItem[] }) {
  if (!citations.length) return null;
  return (
    <div className="mt-3 space-y-2 border-t border-slate-200 pt-2.5">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        Official Evidence &amp; Citations
      </p>
      {citations.map((c, idx) => (
        <div key={idx} className="rounded-lg border border-slate-200 bg-white p-2.5 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-1">
            <span className="font-semibold text-slate-800">
              {c.title}
              {c.page_number ? ` (Page ${c.page_number})` : ""}
            </span>
            <a
              href={c.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-blue-700 hover:underline"
            >
              Official Source <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <p className="mt-1 line-clamp-2 text-slate-600">{c.excerpt}</p>
        </div>
      ))}
    </div>
  );
}

function LiveVerificationList({ items }: { items: LiveVerificationResult[] }) {
  if (!items.length) return null;
  return (
    <div className="mt-3 space-y-2 border-t border-slate-200 pt-2.5">
      <p className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        <Globe2 className="h-3.5 w-3.5" />
        Live Official Website Checks
      </p>
      {items.map((lv, idx) => (
        <div key={idx} className="rounded-lg border border-slate-200 bg-white p-2.5 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 font-semibold text-slate-900">
              {lv.verified_live ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
              ) : (
                <XCircle className="h-3.5 w-3.5 text-rose-600" />
              )}
              {lv.title}
            </span>
            <span className="text-[11px] text-slate-500">
              {lv.verified_live
                ? `HTTP ${lv.http_status} • ${formatDateTime(lv.checked_at)}`
                : "Not reachable"}
            </span>
          </div>
          <a
            href={lv.url}
            target="_blank"
            rel="noreferrer"
            className="mt-0.5 inline-flex items-center gap-1 text-blue-700 hover:underline break-all"
          >
            {lv.url} <ExternalLink className="h-3 w-3 shrink-0" />
          </a>
          {lv.error && <p className="mt-1 text-rose-700">{lv.error}</p>}
          {lv.discovered_links.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {lv.discovered_links.slice(0, 3).map((dl, i) => (
                <a
                  key={i}
                  href={dl.url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-700 hover:bg-slate-100"
                >
                  {dl.label}
                </a>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function AssistantPage() {
  const [searchParams] = useSearchParams();
  const scholarshipId = searchParams.get("scholarship") || null;
  const queryClient = useQueryClient();
  const [message, setMessage] = useState("");
  const [lastLiveChecks, setLastLiveChecks] = useState<LiveVerificationResult[]>([]);
  const [lastError, setLastError] = useState<string | null>(null);

  const { data: status } = useQuery<{
    gemini_configured: boolean;
    model: string | null;
    fallback_mode: string;
  }>({
    queryKey: ["assistant", "status"],
    queryFn: () => apiFetch("/assistant/status"),
  });

  const { data: history, isLoading } = useQuery<AssistantHistoryItem[]>({
    queryKey: ["assistant", "history"],
    queryFn: () => apiFetch<AssistantHistoryItem[]>("/assistant/history"),
  });

  const chatMutation = useMutation({
    mutationFn: (text: string) =>
      apiFetch<AssistantChatResponse>("/assistant/chat", {
        method: "POST",
        body: JSON.stringify({ message: text, scholarship_id: scholarshipId }),
      }),
    onSuccess: (res) => {
      setMessage("");
      setLastError(null);
      setLastLiveChecks(res.live_verifications || []);
      queryClient.invalidateQueries({ queryKey: ["assistant", "history"] });
    },
    onError: (err) => {
      setLastError(err instanceof ApiError ? err.message : "Failed to contact discovery agent.");
    },
  });

  const clearMutation = useMutation({
    mutationFn: () => apiFetch("/assistant/history", { method: "DELETE" }),
    onSuccess: () => {
      setLastLiveChecks([]);
      queryClient.invalidateQueries({ queryKey: ["assistant", "history"] });
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!message.trim() || chatMutation.isPending) return;
    chatMutation.mutate(message.trim());
  };

  const quickPrompts = [
    "I'm an Indian student looking for fully funded Master's scholarships in UK or France",
    "Check official websites for PhD scholarships in Europe or Japan open to Indians",
    "Which AICTE scholarships in India match my current profile right now?",
  ];

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900">
            <Bot className="h-6 w-6 text-slate-800" />
            ScholarSync Discovery Agent
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Searches both ScholarSync&apos;s India &amp; international catalogue and live official
            scholarship websites, verifies what it can reach, and runs deterministic eligibility
            checks.
          </p>
        </div>

        <button
          type="button"
          onClick={() => clearMutation.mutate()}
          disabled={clearMutation.isPending}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Clear history
        </button>
      </div>

      {status && !status.gemini_configured && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
          <div>
            <p className="font-semibold">
              Gemini API key not configured (Deterministic + Live Official Web Mode Active)
            </p>
            <p className="mt-0.5 text-xs text-amber-800">
              <code>GEMINI_API_KEY</code> is not set yet. You can still describe what you want below —
              ScholarSync will parse your requirements, evaluate deterministic rules, and check live
              official scholarship websites.
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {quickPrompts.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => chatMutation.mutate(p)}
            disabled={chatMutation.isPending}
            className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
          >
            {p}
          </button>
        ))}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
        <div className="max-h-[480px] space-y-4 overflow-y-auto pr-1">
          {isLoading ? (
            <p className="text-sm text-slate-500">Loading conversation...</p>
          ) : !history || history.length === 0 ? (
            <div className="py-10 text-center text-sm text-slate-500">
              Describe your target country, university, degree, funding need, or field of study —
              the agent will search the catalogue and live official websites.
            </div>
          ) : (
            history.map((item, index) => {
              const isLatestAssistant =
                item.role === "assistant" && index === history.length - 1;
              return (
                <div
                  key={item.id}
                  className={`rounded-xl p-4 text-sm ${
                    item.role === "user"
                      ? "ml-8 bg-slate-900 text-white"
                      : "mr-4 border border-slate-200 bg-slate-50 text-slate-800"
                  }`}
                >
                  <div className="mb-1 flex items-center justify-between text-[11px] opacity-75">
                    <span className="font-semibold">
                      {item.role === "user" ? "You" : "ScholarSync Discovery Agent"}
                    </span>
                    {item.role === "assistant" && <span>Mode: {item.mode}</span>}
                  </div>
                  <div className="whitespace-pre-wrap leading-relaxed">{item.content}</div>
                  {item.role === "assistant" && isLatestAssistant && lastLiveChecks.length > 0 && (
                    <LiveVerificationList items={lastLiveChecks} />
                  )}
                  {item.role === "assistant" && <CitationList citations={item.citations} />}
                </div>
              );
            })
          )}
        </div>

        {lastError && (
          <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800">
            {lastError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 flex gap-2 border-t border-slate-100 pt-4">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Describe country, course, degree level, funding, or ask about a specific scheme..."
            className="flex-1 rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm focus:border-slate-900 focus:outline-none"
          />
          <button
            type="submit"
            disabled={chatMutation.isPending || !message.trim()}
            className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            {chatMutation.isPending ? "Discovering & verifying..." : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}
