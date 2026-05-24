export interface PlanDay {
  day: number;
  title: string;
  topic: string;
  duration_minutes: number;
}

interface Props {
  days: PlanDay[];
  daysCompleted: number[];
  currentDay?: number | null;
  checkpointEvery: number;
}

function dayState(
  day: number,
  completed: number[],
  currentDay?: number | null
): "done" | "active" | "pending" {
  if (completed.includes(day)) return "done";
  if (currentDay === day) return "active";
  return "pending";
}

export function DayPlanChecklist({ days, daysCompleted, currentDay, checkpointEvery }: Props) {
  return (
    <div className="bg-slate-800 rounded-xl p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-100">Course plan</h3>
        <span className="text-xs text-slate-400">Checkpoint every {checkpointEvery} days</span>
      </div>
      <ol className="max-h-64 overflow-y-auto flex flex-col gap-1 text-xs">
        {days.map((d) => {
          const state = dayState(d.day, daysCompleted, currentDay);
          const isCheckpoint = d.day % checkpointEvery === 0;
          return (
            <li
              key={d.day}
              className={`flex items-start gap-2 rounded-lg px-2 py-1.5 ${
                state === "active"
                  ? "bg-violet-900/40 ring-1 ring-violet-500/50 text-violet-100"
                  : state === "done"
                    ? "text-emerald-400/90"
                    : "text-slate-500"
              }`}
            >
              <span aria-hidden className="w-5 shrink-0 text-center">
                {state === "done" ? "✓" : state === "active" ? "●" : "○"}
              </span>
              <span className="min-w-0 flex-1">
                <span className="font-medium">
                  Day {String(d.day).padStart(2, "0")}: {d.title}
                </span>
                <span className="block truncate opacity-75">{d.topic}</span>
              </span>
              {isCheckpoint && (
                <span className="shrink-0 text-[10px] uppercase tracking-wide text-amber-400/80">
                  review
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
