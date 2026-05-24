import { useState } from "react";
import axios from "axios";
import { startGeneration } from "../api/client";
import { ChatInput } from "./ChatInput";

interface Props {
  onStarted: (sessionId: string) => void;
}

const SUGGESTIONS = [
  "Python list comprehensions",
  "Introduction to neural networks",
  "Git branching and merging",
  "REST API design basics",
];

export function WelcomeScreen({ onStarted }: Props) {
  const [topic, setTopic] = useState("");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async (e: React.FormEvent, text?: string) => {
    e.preventDefault();
    const trimmed = (text ?? topic).trim();
    if (trimmed.length < 3) {
      setError("Topic must be at least 3 characters.");
      return;
    }
    setError(null);
    setStarting(true);
    try {
      const res = await startGeneration(trimmed);
      setTopic("");
      onStarted(res.session_id);
    } catch (err: unknown) {
      let message = "Could not start generation.";
      if (axios.isAxiosError(err) && err.response?.data) {
        const detail = (err.response.data as { detail?: string }).detail;
        if (typeof detail === "string") message = detail;
      }
      setError(message);
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 pb-8 min-h-0">
      <div className="w-full max-w-2xl flex flex-col items-center gap-8">
        <div className="text-center">
          <h1 className="text-3xl font-semibold text-white tracking-tight">
            What would you like to teach?
          </h1>
          <p className="text-white/50 text-sm mt-2 max-w-md mx-auto">
            Enter a topic to generate student notes, tutor guides, diagrams, and a full quality review.
          </p>
        </div>

        <div className="w-full">
          <ChatInput
            value={topic}
            onChange={setTopic}
            onSubmit={handleStart}
            placeholder="e.g. Python decorators and closures"
            disabled={starting}
            loading={starting}
            minLength={3}
            submitLabel="Generate notes"
            rows={2}
          />
          {error && (
            <p className="text-sm text-red-400 mt-2 px-2" role="alert">
              {error}
            </p>
          )}
        </div>

        <div className="flex flex-wrap justify-center gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              disabled={starting}
              onClick={(e) => {
                setTopic(s);
                handleStart(e, s);
              }}
              className="text-sm px-4 py-2 rounded-full border border-white/10 text-white/60
                         hover:bg-white/[0.06] hover:text-white/90 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
