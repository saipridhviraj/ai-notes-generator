import React, { useState, useId } from "react";
import { startGeneration } from "../api/client";

interface Props {
  onSessionStarted: (sessionId: string) => void;
}

export function GenerateForm({ onSessionStarted }: Props) {
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputId = useId();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = topic.trim();
    if (trimmed.length < 3) {
      setError("Topic must be at least 3 characters.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await startGeneration(trimmed);
      onSessionStarted(res.session_id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to start generation.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section aria-labelledby="generate-heading" className="max-w-xl mx-auto">
      <h2 id="generate-heading" className="text-xl font-semibold text-slate-100 mb-1">
        Single lesson
      </h2>
      <p className="text-sm text-slate-400 mb-4">
        One topic → student + tutor notes with a plan review before generation.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label htmlFor={inputId} className="text-sm text-slate-400">
          Lesson topic
        </label>
        <input
          id={inputId}
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. Python Decorators"
          maxLength={500}
          aria-required="true"
          aria-describedby={error ? "topic-error" : undefined}
          className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-4 py-2.5
                     focus:outline-none focus:ring-2 focus:ring-violet-500 placeholder:text-slate-500"
        />
        {error && (
          <p id="topic-error" role="alert" className="text-red-400 text-sm">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={loading}
          aria-busy={loading}
          className="bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white font-medium
                     rounded-lg px-6 py-2.5 transition-colors focus:outline-none focus:ring-2
                     focus:ring-violet-400"
        >
          {loading ? "Starting…" : "Generate"}
        </button>
      </form>
    </section>
  );
}
