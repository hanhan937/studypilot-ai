
import { useEffect, useState, type FormEvent } from "react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type StudyTask = {
  id: number;
  title: string;
  scheduled_date: string | null;
  estimated_minutes: number | null;
  completed: boolean;
};

type StudyPlan = {
  id: number;
  goal: string;
  start_date: string;
  end_date: string;
  daily_minutes: number;
  tasks: StudyTask[];
};

async function apiRequest(
  url: string,
  options?: RequestInit
) {
  const response = await fetch(`${API_BASE_URL}${url}`, options);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error ?? "Request failed.");
  }

  return data;
}

export default function StudyPlans({
  onTasksChanged,
}: {
  onTasksChanged?: () => void;
}) {
  const [goal, setGoal] = useState("");
  const [days, setDays] = useState(7);
  const [dailyMinutes, setDailyMinutes] = useState(120);

  const [plans, setPlans] = useState<StudyPlan[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadPlans() {
    setLoading(true);
    try {
      const data = await apiRequest("/api/plans/");
      setPlans(data.plans);
      setError("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load plans."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPlans();
  }, []);

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;

    setBusy(true);
    setError("");

    try {
      await apiRequest("/api/plans/generate/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          goal,
          days,
          daily_minutes: dailyMinutes,
        }),
      });

      setGoal("");
      await loadPlans();
      onTasksChanged?.();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to generate plan."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleReschedule(planId: number) {
    if (busy) return;

    setBusy(true);
    setError("");

    try {
      await apiRequest(`/api/plans/${planId}/reschedule/`, {
        method: "POST",
      });

      await loadPlans();
      onTasksChanged?.();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to reschedule."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-5 rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-bold text-slate-900">
        Study Plans
      </h2>

      <form onSubmit={handleGenerate} className="space-y-3">
        <div>
          <label className="block text-sm font-medium">
            Learning Goal
          </label>
          <input
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Prepare for coding interviews"
            required
            maxLength={500}
            className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-sm"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium">
              Days
            </label>
            <input
              type="number"
              min={1}
              max={30}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              required
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium">
              Minutes / Day
            </label>
            <input
              type="number"
              min={15}
              max={480}
              value={dailyMinutes}
              onChange={(e) => setDailyMinutes(Number(e.target.value))}
              required
              className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-indigo-600 p-2.5 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {busy ? "Working..." : "Generate Plan"}
        </button>
      </form>

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Saved Plans</h3>
          <button
            onClick={() => void loadPlans()}
            disabled={loading || busy}
            className="text-sm text-indigo-600 disabled:opacity-50"
          >
            Refresh
          </button>
        </div>

        {loading && <p className="text-sm text-slate-500">Loading...</p>}

        {!loading && plans.length === 0 && (
          <p className="text-sm text-slate-500">No study plans yet.</p>
        )}

        {plans.map((plan) => {
          const completed = plan.tasks.filter(
            (task) => task.completed
          ).length;

          return (
            <div
              key={plan.id}
              className="space-y-3 rounded-lg border border-slate-200 p-3"
            >
              <div>
                <h4 className="font-semibold text-slate-900">
                  {plan.goal}
                </h4>
                <p className="text-xs text-slate-500">
                  {plan.start_date} to {plan.end_date}
                </p>
                <p className="text-xs text-slate-500">
                  {plan.daily_minutes} min/day ·{" "}
                  {completed}/{plan.tasks.length} completed
                </p>
              </div>

              <ul className="space-y-2">
                {plan.tasks.map((task) => (
                  <li
                    key={task.id}
                    className="rounded-md bg-slate-50 p-2 text-sm"
                  >
                    <span className={task.completed ? "line-through text-slate-400" : ""}>
                      {task.completed ? "✓ " : "○ "}
                      {task.title}
                    </span>
                    <p className="text-xs text-slate-500">
                      {task.scheduled_date ?? "Unscheduled"}
                      {" · "}
                      {task.estimated_minutes ?? 0} min
                    </p>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => void handleReschedule(plan.id)}
                disabled={busy}
                className="rounded-lg border border-indigo-200 px-3 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50 disabled:opacity-50"
              >
                Reschedule
              </button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
