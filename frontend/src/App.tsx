import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import StudyPlans from "./StudyPlans";

// ---------- Configuration ----------
// Uses the existing VITE_API_BASE_URL from frontend/.env (falls back to the local Django server).
const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const MAX_MESSAGE_LENGTH = 2000; // keep in sync with the backend limit
const EXAMPLE_PROMPT = "I want to prepare for coding interviews in 7 days.";
// The fixed commands Demo Mode understands (shown as clickable examples in Demo Mode only).
const DEMO_COMMANDS = [
  "Create a task called Binary Search",
  "Show my tasks",
  "Mark Binary Search as completed",
  "What's my study progress?",
];

// ---------- Types ----------
type Mode = "demo" | "real";

type Task = {
  id: number;
  title: string;
  topic: string;
  scheduled_date?: string | null;
  estimated_minutes?: number | null;
  completed: boolean;
  created_at?: string;
};

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
  mode?: Mode; // set on assistant messages: which mode produced this reply
};

// ---------- API helpers (all backend calls live here) ----------

/** GET /api/tasks/ -> the list of saved tasks. Throws Error with a friendly message on failure. */
async function fetchTasks(): Promise<Task[]> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/tasks/`);
  } catch {
    throw new Error(`Could not reach the backend at ${API_BASE_URL}. Is Django running?`);
  }
  if (!response.ok) {
    throw new Error(`Could not load tasks (the server returned status ${response.status}).`);
  }

  const data: unknown = await response.json().catch(() => null);
  const tasks = (data as { tasks?: unknown } | null)?.tasks;
  if (!Array.isArray(tasks)) {
    throw new Error("Unexpected response from /api/tasks/.");
  }
  return tasks as Task[];
}

/** POST /api/chat/ -> { reply, mode }. Throws Error with a friendly message on failure. */
async function sendChatMessage(message: string): Promise<{ reply: string; mode: Mode }> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
  } catch {
    throw new Error(`Could not reach the backend. Is Django running on ${API_BASE_URL}?`);
  }

  const body = (await response.json().catch(() => null)) as {
    reply?: string;
    error?: string;
    mode?: string;
  } | null;

  if (!response.ok) {
    throw new Error(body?.error ?? `Request failed with status ${response.status}.`);
  }
  if (!body?.reply) {
    throw new Error("The server returned an unexpected response.");
  }
  // The backend tells us explicitly which mode answered.
  return { reply: body.reply, mode: body.mode === "demo" ? "demo" : "real" };
}

/** GET /api/config/ -> is Demo Mode on? Never throws: if the call fails we assume it is off. */
async function fetchDemoMode(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/config/`);
    if (!response.ok) return false;
    const body = (await response.json()) as { mock_ai?: boolean };
    return body.mock_ai === true;
  } catch {
    return false;
  }
}

// ---------- Small components ----------

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
      {message.mode === "demo" && (
        <span className="mb-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 ring-1 ring-amber-300">
          Demo Mode
        </span>
      )}
      <div
        className={`max-w-[85%] whitespace-pre-wrap break-words rounded-2xl px-4 py-2.5 text-sm leading-relaxed sm:text-base ${
          isUser
            ? "rounded-br-sm bg-indigo-600 text-white"
            : "rounded-bl-sm bg-white text-slate-800 shadow-sm ring-1 ring-slate-200"
        }`}
      >
        {message.text}
      </div>
    </div>
  );
}

function TaskItem({ task }: { task: Task }) {
  return (
    <li className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-3">
      <span
        aria-hidden="true"
        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
          task.completed ? "bg-emerald-500 text-white" : "border-2 border-slate-300"
        }`}
      >
        {task.completed ? "✓" : ""}
      </span>

      <div className="min-w-0 flex-1">
        <p
          className={`break-words text-sm font-medium ${
            task.completed ? "text-slate-400 line-through" : "text-slate-900"
          }`}
        >
          {task.title}
        </p>
        <p className="break-words text-xs text-slate-500">Topic: {task.topic}</p>
      </div>

      <span
        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
          task.completed ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"
        }`}
      >
        {task.completed ? "Completed" : "To do"}
      </span>
    </li>
  );
}

// ---------- Main component ----------

export default function App() {
  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const nextMessageId = useRef(1);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Task list state
  const [tasks, setTasks] = useState<Task[]>([]);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [tasksError, setTasksError] = useState<string | null>(null);
  const latestTasksRequest = useRef(0);

  /** Load tasks from the backend. Safe to call many times: only the newest request updates the UI. */
  const loadTasks = useCallback(async () => {
    const requestId = ++latestTasksRequest.current;
    setTasksLoading(true);
    setTasksError(null);
    try {
      const loaded = await fetchTasks();
      if (requestId !== latestTasksRequest.current) return;
      setTasks(loaded);
    } catch (err) {
      if (requestId !== latestTasksRequest.current) return;
      setTasksError(err instanceof Error ? err.message : "Could not load tasks.");
    } finally {
      if (requestId === latestTasksRequest.current) setTasksLoading(false);
    }
  }, []);

  // When the page loads: fetch the tasks and check whether Demo Mode is on.
  useEffect(() => {
    loadTasks();
    fetchDemoMode().then(setDemoMode);
  }, [loadTasks]);

  // Keep the newest chat message in view.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending, chatError]);

  function addMessage(role: ChatMessage["role"], text: string, mode?: Mode) {
    setMessages((prev) => [...prev, { id: nextMessageId.current++, role, text, mode }]);
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;

    addMessage("user", text);
    setInput("");
    setChatError(null);
    setSending(true);

    try {
      const { reply, mode } = await sendChatMessage(text);
      addMessage("assistant", reply, mode);
      setDemoMode(mode === "demo"); // the response itself says which mode answered
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSending(false);
      // A command may have created or completed a task, so show the latest database state.
      loadTasks();
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter inserts a new line.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  const completedCount = tasks.filter((task) => task.completed).length;

  return (
    <div className="flex h-screen flex-col bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white px-4 py-3">
        <div className="mx-auto max-w-5xl">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-900">StudyPilot AI</h1>
            {demoMode && (
              <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800 ring-1 ring-amber-300">
                Demo Mode
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500">Tell me your learning goal and I'll plan it with you.</p>
        </div>
      </header>

      {demoMode && (
        <div
          role="status"
          className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-sm text-amber-800"
        >
          Demo Mode is on: no AI model is used. Only a few fixed task commands work, and tasks are
          really saved in the database.
        </div>
      )}

      {/* Body: task list (above the chat on small screens, sidebar on large screens) + chat */}
      <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 flex-col gap-4 overflow-y-auto px-4 py-4 lg:flex-row">
        {/* ----- Study Task List ----- */}
        <section
          aria-label="Study Task List"
          className="flex max-h-56 shrink-0 flex-col rounded-xl bg-slate-100/60 p-3 ring-1 ring-slate-200 lg:order-2 lg:max-h-none lg:w-80"
        >
          <div className="mb-2 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-800">
              Study Task List
              {tasks.length > 0 && (
                <span className="ml-2 font-normal text-slate-500">
                  {completedCount}/{tasks.length} done
                </span>
              )}
            </h2>
            <button
              onClick={loadTasks}
              disabled={tasksLoading}
              className="rounded-md bg-white px-2.5 py-1 text-xs font-medium text-indigo-600 ring-1 ring-slate-200 transition hover:bg-indigo-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {tasksLoading ? "Refreshing..." : "Refresh Tasks"}
            </button>
          </div>

          {tasksError && (
            <p role="alert" className="mb-2 rounded bg-red-50 p-2 text-xs text-red-700">
              {tasksError}
            </p>
          )}

          <div className="min-h-0 flex-1 overflow-y-auto">
            {tasks.length > 0 ? (
              <ul className="flex flex-col gap-2">
                {tasks.map((task) => (
                  <TaskItem key={task.id} task={task} />
                ))}
              </ul>
            ) : tasksLoading ? (
              <p className="animate-pulse p-3 text-center text-sm text-slate-500">Loading tasks...</p>
            ) : tasksError ? null : (
              <p className="p-3 text-center text-sm text-slate-500">
                No tasks yet. Ask StudyPilot to add one.
              </p>
            )}
          </div>
        </section>

        {/* ----- Study Plans ----- */}
<section className="w-full shrink-0 lg:w-80">
  <StudyPlans onTasksChanged={() => void loadTasks()} />
</section>
        
        {/* ----- Chat messages ----- */}
        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="flex flex-col gap-3">
            {messages.length === 0 && (
              <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-slate-500">
                <p>{demoMode ? "Try one of the Demo Mode commands:" : "What do you want to learn?"}</p>
                <div className="mt-3 flex flex-wrap justify-center gap-2">
                  {demoMode ? (
                    DEMO_COMMANDS.map((command) => (
                      <button
                        key={command}
                        onClick={() => setInput(command)}
                        className="rounded-lg bg-white px-3 py-1.5 text-sm text-amber-700 ring-1 ring-amber-200 hover:bg-amber-50"
                      >
                        {command}
                      </button>
                    ))
                  ) : (
                    <button
                      onClick={() => setInput(EXAMPLE_PROMPT)}
                      className="rounded-lg bg-white px-3 py-1.5 text-sm text-indigo-600 ring-1 ring-slate-200 hover:bg-indigo-50"
                    >
                      Try: "{EXAMPLE_PROMPT}"
                    </button>
                  )}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}

            {sending && (
              <div className="flex justify-start">
                <div className="animate-pulse rounded-2xl rounded-bl-sm bg-white px-4 py-2.5 text-slate-500 shadow-sm ring-1 ring-slate-200">
                  StudyPilot is working...
                </div>
              </div>
            )}

            {chatError && (
              <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                {chatError}
              </p>
            )}

            <div ref={bottomRef} />
          </div>
        </main>
      </div>

      {/* Chat input */}
      <footer className="border-t border-slate-200 bg-white px-4 py-3">
        {/* On large screens, leave room on the right so the input lines up with the chat column. */}
        <div className="mx-auto flex max-w-5xl items-end gap-2 lg:pr-[336px]">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            maxLength={MAX_MESSAGE_LENGTH}
            rows={2}
            placeholder={demoMode ? "Type a Demo Mode command..." : "Describe your learning goal..."}
            disabled={sending}
            className="flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100 sm:text-base"
          />
          <button
            onClick={handleSend}
            disabled={sending || input.trim() === ""}
            className="rounded-lg bg-indigo-600 px-5 py-2.5 font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </footer>
    </div>
  );
}