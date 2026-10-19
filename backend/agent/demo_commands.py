"""
Demo Mode (MOCK_AI=true): deterministic task commands.

There is NO language model here and NO OpenAI request. A message is compared with a few fixed
text patterns (regular expressions). If one matches, we run the matching function from
agent/task_service.py (the same functions the real agent tools use). Anything else gets a
fallback message. This is pattern matching, not AI reasoning, and the replies say so.

Safety rule: we only report success after READING THE DATABASE BACK and seeing the change.
(We do not simply trust a function's return value.)

Supported commands (case-insensitive):
    Create a task called Binary Search
    Show my tasks
    Mark Binary Search as completed        (also: "Mark task 3 as completed")
    What's my study progress?
"""
import inspect
import logging
import re

from agent import task_service

logger = logging.getLogger(__name__)

DEFAULT_TOPIC = "General"
LABEL = "[Demo Mode] "
FOOTER = (
    "\n\n(Demo Mode: this command was matched by a fixed text pattern, "
    "not AI reasoning. No AI model was used.)"
)

FALLBACK_REPLY = (
    "Sorry, I don't recognize that command. In Demo Mode I cannot understand free-form "
    "requests (that needs a real AI model). I only match these fixed commands:\n"
    "- Create a task called Binary Search\n"
    "- Show my tasks\n"
    "- Mark Binary Search as completed\n"
    "- What's my study progress?\n\n"
    "To chat with the real StudyPilot agent, set MOCK_AI=false and add an OpenAI API key."
)

# ---------- Command patterns ----------
_FLAGS = re.IGNORECASE
_CREATE = re.compile(
    r"^(?:create|add)\s+(?:an?\s+|new\s+)*task(?:\s+(?:called|named|titled)\s+|\s*:\s*)"
    r"(?P<title>.+?)\s*[.!]?$",
    _FLAGS,
)
_LIST = re.compile(
    r"^(?:show|list|view|what\s+are)\s+(?:me\s+)?(?:my\s+|all\s+)?"
    r"(?:(?P<status>pending|incomplete|completed|done)\s+)?tasks?\s*[.?!]?$",
    _FLAGS,
)
_COMPLETE_MARK = re.compile(
    r"^(?:mark|set)\s+(?P<target>.+?)\s+as\s+(?:completed|complete|done|finished)\s*[.!]?$",
    _FLAGS,
)
_COMPLETE_VERB = re.compile(r"^(?:complete|finish)\s+(?P<target>.+?)\s*[.!]?$", _FLAGS)
_PROGRESS = re.compile(
    r"^(?:(?:what(?:['’]s|\s+is)|show|check)\s+)?(?:my\s+)?(?:study\s+)?progress\s*[.?!]?$",
    _FLAGS,
)
_TASK_ID = re.compile(r"(?:task\s+)?#?(\d+)", _FLAGS)

_STATUS_FILTERS = {
    None: None,
    "pending": False,
    "incomplete": False,
    "completed": True,
    "done": True,
}


class DemoCommandError(Exception):
    """A task operation failed. The message is safe to show to the user."""


# ---------- Safe wrappers around agent/task_service.py ----------

def _check_result(result):
    """If a service function reports failure in its return value ({"ok": False, ...}), raise."""
    if isinstance(result, dict) and result.get("ok") is False:
        message = result.get("message") or result.get("error") or "The operation failed."
        raise DemoCommandError(str(message))
    return result


def _call(function, *args, **kwargs):
    """Call a task_service function. Any failure becomes a DemoCommandError."""
    try:
        return _check_result(function(*args, **kwargs))
    except DemoCommandError:
        raise
    except ValueError as exc:  # validation errors written by us; safe to show
        raise DemoCommandError(str(exc)) from exc
    except Exception as exc:
        # Log only the error type, then show a generic message.
        logger.error("task_service.%s failed (%s)", function.__name__, type(exc).__name__)
        raise DemoCommandError("The database operation failed.") from exc


def _as_dict(task) -> dict:
    """Turn a task (dict or model object) into a plain dict with the fields we need."""
    if isinstance(task, dict):
        get = task.get
    else:
        def get(key, default=None):
            return getattr(task, key, default)

    return {
        "id": get("id"),
        "title": str(get("title", "") or ""),
        "topic": str(get("topic", "") or ""),
        "completed": bool(get("completed", False)),
    }


def _read_tasks() -> list[dict]:
    """Read ALL tasks straight from the database through task_service.list_tasks()."""
    result = _call(task_service.list_tasks)
    if isinstance(result, dict):
        result = result.get("tasks", [])
    return [_as_dict(task) for task in result]


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _describe(task: dict) -> str:
    box = "[x]" if task["completed"] else "[ ]"
    topic = f" ({task['topic']})" if task["topic"] else ""
    return f"{box} #{task['id']} {task['title']}{topic}"


# ---------- Command handlers ----------

def _create(title: str) -> str:
    ids_before = {task["id"] for task in _read_tasks()}

    # Pass a default topic only if create_task has a "topic" parameter.
    kwargs = {}
    if "topic" in inspect.signature(task_service.create_task).parameters:
        kwargs["topic"] = DEFAULT_TOPIC
    _call(task_service.create_task, title, **kwargs)

    # Verify: a brand-new row must now exist in the database.
    new_tasks = [task for task in _read_tasks() if task["id"] not in ids_before]
    if not new_tasks:
        raise DemoCommandError("The task was not found in the database afterwards, so it was NOT saved.")
    task = new_tasks[0]
    return f"Created task #{task['id']}: {task['title']} (topic: {task['topic'] or DEFAULT_TOPIC})."


def _list(status_word) -> str:
    wanted = _STATUS_FILTERS[status_word.lower() if status_word else None]
    tasks = _read_tasks()
    if wanted is not None:
        tasks = [task for task in tasks if task["completed"] == wanted]

    if not tasks:
        return "You have no tasks yet." if wanted is None else "No matching tasks found."
    return "Your tasks:\n" + "\n".join(f"- {_describe(task)}" for task in tasks)


def _complete(target: str) -> str:
    tasks = _read_tasks()

    # Step 1: resolve the title (or "task 3") to task IDs.
    id_match = _TASK_ID.fullmatch(target)
    if id_match:
        matches = [task for task in tasks if str(task["id"]) == id_match.group(1)]
    else:
        wanted = _normalize(target)
        matches = [task for task in tasks if _normalize(task["title"]) == wanted]  # exact title first
        if not matches:
            matches = [task for task in tasks if wanted in _normalize(task["title"])]  # then partial

    if not matches:
        return f'I could not find a task matching "{target}". Nothing was changed.'
    if len(matches) > 1:
        lines = "\n".join(f"- {_describe(task)}" for task in matches)
        return (
            f'More than one task matches "{target}", so I did not change anything. '
            f"Which one do you mean?\n{lines}\n"
            f'Reply with an id, for example: "Mark task {matches[0]["id"]} as completed".'
        )

    task = matches[0]
    if task["completed"]:
        return f'Task #{task["id"]} "{task["title"]}" is already completed. Nothing was changed.'

    # Step 2: update by ID, then verify in the database.
    _call(task_service.complete_task, task["id"])
    updated = {t["id"]: t for t in _read_tasks()}.get(task["id"])
    if not updated or not updated["completed"]:
        raise DemoCommandError("The database does not show the task as completed, so it was NOT updated.")
    return f'Marked task #{task["id"]} as completed: {task["title"]}.'


def _first_int(data: dict, keys: tuple):
    for key in keys:
        value = data.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _progress() -> str:
    result = _call(task_service.get_progress)
    data = result if isinstance(result, dict) else {}
    if isinstance(data.get("progress"), dict):  # some versions nest the numbers under "progress"
        data = data["progress"]

    total = _first_int(data, ("total", "total_tasks", "count"))
    completed = _first_int(data, ("completed", "completed_tasks", "done"))
    if total is None or completed is None:
        # get_progress used field names we do not know: count from the database instead.
        tasks = _read_tasks()
        total = len(tasks)
        completed = sum(1 for task in tasks if task["completed"])

    percent = round(completed / total * 100, 1) if total else 0.0
    return f"Study progress: {completed} of {total} task(s) completed ({percent}%)."


# ---------- Entry point ----------

def _dispatch(text: str) -> str:
    if _PROGRESS.match(text):
        return _progress()
    if match := _LIST.match(text):
        return _list(match.group("status"))
    if match := _CREATE.match(text):
        return _create(match.group("title").strip())
    if match := (_COMPLETE_MARK.match(text) or _COMPLETE_VERB.match(text)):
        return _complete(match.group("target").strip())
    return FALLBACK_REPLY


def handle_demo_command(message: str) -> str:
    """Run a supported demo command, or return the fallback message. Never calls OpenAI."""
    text = " ".join(message.split())
    try:
        reply = _dispatch(text)
    except DemoCommandError as exc:
        reply = f"Sorry, that did not work: {exc}"
    return f"{LABEL}{reply}{FOOTER}"