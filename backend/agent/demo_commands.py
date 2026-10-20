
"""
Demo Mode (MOCK_AI=true): deterministic task commands.

No language model or OpenAI request is used.

Supported commands:
    Create a task called Binary Search
    Show my tasks
    Mark Binary Search as completed
    Mark task 3 as completed
    What's my study progress?

All task operations are scoped to the current guest session.

Safety rule:
Only report success after reading the database back
and verifying the change.
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
    "Sorry, I don't recognize that command. In Demo Mode I cannot understand "
    "free-form requests (that needs a real AI model). "
    "I only match these fixed commands:\n"
    "- Create a task called Binary Search\n"
    "- Show my tasks\n"
    "- Mark Binary Search as completed\n"
    "- What's my study progress?\n\n"
    "To chat with the real StudyPilot agent, set MOCK_AI=false "
    "and add an OpenAI API key."
)


# ---------- Command patterns ----------

_FLAGS = re.IGNORECASE

_CREATE = re.compile(
    r"^(?:create|add)\s+(?:an?\s+|new\s+)*task"
    r"(?:\s+(?:called|named|titled)\s+|\s*:\s*)"
    r"(?P<title>.+?)\s*[.!]?$",
    _FLAGS,
)

_LIST = re.compile(
    r"^(?:show|list|view|what\s+are)\s+"
    r"(?:me\s+)?(?:my\s+|all\s+)?"
    r"(?:(?P<status>pending|incomplete|completed|done)\s+)?"
    r"tasks?\s*[.?!]?$",
    _FLAGS,
)

_COMPLETE_MARK = re.compile(
    r"^(?:mark|set)\s+(?P<target>.+?)\s+as\s+"
    r"(?:completed|complete|done|finished)\s*[.!]?$",
    _FLAGS,
)

_COMPLETE_VERB = re.compile(
    r"^(?:complete|finish)\s+(?P<target>.+?)\s*[.!]?$",
    _FLAGS,
)

_PROGRESS = re.compile(
    r"^(?:(?:what(?:['’]s|\s+is)|show|check)\s+)?"
    r"(?:my\s+)?(?:study\s+)?progress\s*[.?!]?$",
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
    """A task operation failed. Safe to show to the user."""


# ---------- Safe task service wrappers ----------

def _check_result(result):
    """Detect service functions that return an explicit failure."""
    if isinstance(result, dict) and result.get("ok") is False:
        message = (
            result.get("message")
            or result.get("error")
            or "The operation failed."
        )
        raise DemoCommandError(str(message))

    return result


def _call(function, *args, **kwargs):
    """Convert task service failures into DemoCommandError."""
    try:
        return _check_result(function(*args, **kwargs))

    except DemoCommandError:
        raise

    except ValueError as exc:
        raise DemoCommandError(str(exc)) from exc

    except Exception as exc:
        logger.error(
            "task_service.%s failed (%s)",
            function.__name__,
            type(exc).__name__,
        )
        raise DemoCommandError(
            "The database operation failed."
        ) from exc


def _as_dict(task) -> dict:
    """Convert a task model or dictionary to a simple dictionary."""
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


def _read_tasks(session_key: str) -> list[dict]:
    """Read only tasks belonging to this guest session."""
    result = _call(
        task_service.list_tasks,
        session_key=session_key,
    )

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

def _create(title: str, session_key: str) -> str:
    """Create a task for this session and verify it was saved."""

    ids_before = {
        task["id"]
        for task in _read_tasks(session_key)
    }

    kwargs = {
        "session_key": session_key,
    }

    if "topic" in inspect.signature(
        task_service.create_task
    ).parameters:
        kwargs["topic"] = DEFAULT_TOPIC

    _call(
        task_service.create_task,
        title,
        **kwargs,
    )

    # Verify the newly created task is visible to this session.
    new_tasks = [
        task
        for task in _read_tasks(session_key)
        if task["id"] not in ids_before
    ]

    if not new_tasks:
        raise DemoCommandError(
            "The task was not found in the database afterwards, "
            "so it was NOT saved."
        )

    task = new_tasks[0]

    return (
        f"Created task #{task['id']}: {task['title']} "
        f"(topic: {task['topic'] or DEFAULT_TOPIC})."
    )


def _list(status_word, session_key: str) -> str:
    """List only tasks belonging to this session."""

    wanted = _STATUS_FILTERS[
        status_word.lower() if status_word else None
    ]

    tasks = _read_tasks(session_key)

    if wanted is not None:
        tasks = [
            task
            for task in tasks
            if task["completed"] == wanted
        ]

    if not tasks:
        if wanted is None:
            return "You have no tasks yet."

        return "No matching tasks found."

    return "Your tasks:\n" + "\n".join(
        f"- {_describe(task)}"
        for task in tasks
    )


def _complete(target: str, session_key: str) -> str:
    """Complete a task belonging to this session."""

    tasks = _read_tasks(session_key)

    # Step 1: Find matching tasks.
    id_match = _TASK_ID.fullmatch(target)

    if id_match:
        matches = [
            task
            for task in tasks
            if str(task["id"]) == id_match.group(1)
        ]

    else:
        wanted = _normalize(target)

        # Exact title match first.
        matches = [
            task
            for task in tasks
            if _normalize(task["title"]) == wanted
        ]

        # Partial title match if no exact match.
        if not matches:
            matches = [
                task
                for task in tasks
                if wanted in _normalize(task["title"])
            ]

    if not matches:
        return (
            f'I could not find a task matching "{target}". '
            "Nothing was changed."
        )

    if len(matches) > 1:
        lines = "\n".join(
            f"- {_describe(task)}"
            for task in matches
        )

        return (
            f'More than one task matches "{target}", '
            f"so I did not change anything. "
            f"Which one do you mean?\n{lines}\n"
            f'Reply with an id, for example: '
            f'"Mark task {matches[0]["id"]} as completed".'
        )

    task = matches[0]

    if task["completed"]:
        return (
            f'Task #{task["id"]} "{task["title"]}" '
            "is already completed. Nothing was changed."
        )

    # Step 2: Complete task, scoped to this guest session.
    _call(
        task_service.complete_task,
        task["id"],
        session_key=session_key,
    )

    # Step 3: Verify database state.
    updated = {
        item["id"]: item
        for item in _read_tasks(session_key)
    }.get(task["id"])

    if not updated or not updated["completed"]:
        raise DemoCommandError(
            "The database does not show the task as completed, "
            "so it was NOT updated."
        )

    return (
        f'Marked task #{task["id"]} as completed: '
        f'{task["title"]}.'
    )


def _first_int(data: dict, keys: tuple):
    for key in keys:
        value = data.get(key)

        if isinstance(value, int) and not isinstance(value, bool):
            return value

    return None


def _progress(session_key: str) -> str:
    """Calculate progress for this guest session."""

    result = _call(
        task_service.get_progress,
        session_key=session_key,
    )

    data = result if isinstance(result, dict) else {}

    if isinstance(data.get("progress"), dict):
        data = data["progress"]

    total = _first_int(
        data,
        ("total", "total_tasks", "count"),
    )

    completed = _first_int(
        data,
        ("completed", "completed_tasks", "done"),
    )

    if total is None or completed is None:
        tasks = _read_tasks(session_key)
        total = len(tasks)
        completed = sum(
            1
            for task in tasks
            if task["completed"]
        )

    percent = (
        round(completed / total * 100, 1)
        if total
        else 0.0
    )

    return (
        f"Study progress: {completed} of {total} "
        f"task(s) completed ({percent}%)."
    )


# ---------- Command dispatcher ----------

def _dispatch(text: str, session_key: str) -> str:
    """Match a command and execute it for this session."""

    if _PROGRESS.match(text):
        return _progress(session_key)

    if match := _LIST.match(text):
        return _list(
            match.group("status"),
            session_key,
        )

    if match := _CREATE.match(text):
        return _create(
            match.group("title").strip(),
            session_key,
        )

    if match := (
        _COMPLETE_MARK.match(text)
        or _COMPLETE_VERB.match(text)
    ):
        return _complete(
            match.group("target").strip(),
            session_key,
        )

    return FALLBACK_REPLY


# ---------- Public entry point ----------

def handle_demo_command(
    message: str,
    *,
    session_key: str,
) -> str:
    """
    Run a supported Demo Mode command for one guest session.

    The session_key must come from Django's trusted server-side
    request session, never directly from user-provided JSON.
    """

    # Fail closed if the caller does not supply a valid key.
    # This protects even fallback commands from bypassing
    # the required session context.
    task_service.validate_session_key(session_key)

    text = " ".join(message.split())

    try:
        reply = _dispatch(text, session_key)

    except DemoCommandError as exc:
        reply = f"Sorry, that did not work: {exc}"

    return f"{LABEL}{reply}{FOOTER}"
