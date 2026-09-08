"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui";

type Message = {
  role: "user" | "assistant" | "unavailable";
  text: string;
};

// One id per browser tab, not per question - the ADK session keeps the
// conversation's turns together server-side. Generated once on mount, not
// persisted, so a reload starts a fresh conversation deliberately.
// The backend passes through the raw exception from google-genai
// (ask_copilot's docstring is explicit: "surfaced to the user, not
// masked"). That's the right call for someone debugging the deploy, but
// a live demo shouldn't read a stack-trace-shaped JSON blob out loud -
// so recognise the one failure mode that's actually happened here and
// give it a sentence; anything else still gets the raw reason, honestly.
function friendlyUnavailableReason(reason: string): string {
  if (/401|UNAUTHENTICATED|invalid authentication credentials/i.test(reason)) {
    return "The Gemini API key isn't authenticating right now, so the copilot can't write an explanation. Every score, gap and backtest figure elsewhere in the app is unaffected - none of them go through this key.";
  }
  return reason;
}

function newSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return "web-" + Math.random().toString(36).slice(2);
}

export function CopilotChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const sessionId = useRef(newSessionId());
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, asking]);

  async function send() {
    const q = question.trim();
    if (!q || asking) return;
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setQuestion("");
    setAsking(true);
    try {
      const result = await api.askCopilot(q, sessionId.current);
      if (result.status === "success" && result.answer) {
        setMessages((prev) => [...prev, { role: "assistant", text: result.answer! }]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "unavailable",
            text: result.reason
              ? friendlyUnavailableReason(result.reason)
              : "The copilot didn't return an answer. The deterministic engines - scores, gaps, backtest - are unaffected either way.",
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "unavailable",
          text: "Couldn't reach the API. The rest of the app doesn't depend on this.",
        },
      ]);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-3">
      {open ? (
        <div className="flex h-[480px] w-[360px] flex-col overflow-hidden rounded-[12px] border border-border bg-bg-elevated shadow-[0_12px_32px_-8px_rgba(32,38,44,0.25)]">
          <div className="flex items-center justify-between border-b border-border bg-accent px-4 py-3">
            <div>
              <div className="font-display text-sm font-bold text-accent-ink">Ask Mechnari</div>
              <div className="text-[11px] text-accent-ink/80">
                Explains findings in prose - never scores them
              </div>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
              className="rounded-full px-2 py-1 text-accent-ink/90 hover:bg-black/10"
            >
              ✕
            </button>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3">
            {messages.length === 0 ? (
              <p className="px-1 text-[13px] leading-relaxed text-ink-faint">
                Ask about a part, a failure mode, or why something scored the way it
                did - e.g. &ldquo;why is the crimped ferrule joint High priority?&rdquo;
                Every number it references comes from the same engines the rest of
                the app uses; the model only writes the explanation.
              </p>
            ) : null}
            <div className="flex flex-col gap-2.5">
              {messages.map((m, i) => (
                <ChatBubble key={i} message={m} />
              ))}
              {asking ? (
                <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface px-3 py-2 text-[13px]">
                  <Spinner />
                </div>
              ) : null}
            </div>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
            className="flex items-end gap-2 border-t border-border p-2.5"
          >
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder="Ask a question…"
              rows={1}
              className="min-h-[38px] flex-1 resize-none rounded-[8px] border border-border-strong bg-bg-elevated px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none"
            />
            <button
              type="submit"
              disabled={asking || !question.trim()}
              aria-label="Send"
              className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-[8px] bg-accent text-accent-ink transition-[filter] hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
            >
              ➤
            </button>
          </form>
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close copilot chat" : "Open copilot chat"}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-accent text-2xl text-accent-ink shadow-[0_8px_20px_-4px_rgba(32,38,44,0.35)] transition-[filter,transform] hover:brightness-110 active:scale-95"
      >
        {open ? "✕" : "💬"}
      </button>
    </div>
  );
}

function ChatBubble({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="ml-8 rounded-[10px] rounded-br-[3px] bg-accent-soft px-3 py-2 text-[13px] text-ink">
        {message.text}
      </div>
    );
  }
  if (message.role === "unavailable") {
    return (
      <div className="mr-8 rounded-[10px] rounded-bl-[3px] border border-warn bg-warn-soft px-3 py-2 text-[13px] text-warn">
        {message.text}
      </div>
    );
  }
  return (
    <div className="mr-8 whitespace-pre-wrap rounded-[10px] rounded-bl-[3px] border border-border bg-surface px-3 py-2 text-[13px] leading-relaxed text-ink">
      {message.text}
    </div>
  );
}
