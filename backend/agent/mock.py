"""
Mock Mode: predefined study-planning replies.

Nothing in this file talks to the network or to OpenAI.
"""

_FOOTER = "\n\n(Demo response: no AI model was called.)"

_INTERVIEW_PLAN = """\
Here is a realistic 7-day coding interview plan (about 2 hours per day):

Day 1: Arrays and strings. Solve 3 easy problems.
Day 2: Hash maps and two pointers. Solve 3 problems.
Day 3: Linked lists, stacks and queues. Solve 3 problems.
Day 4: Trees and recursion. Solve 2-3 problems.
Day 5: Sorting, searching and binary search. Solve 3 problems.
Day 6: Mock interview. Do 2 timed problems and explain your thinking out loud.
Day 7: Review your mistakes, redo 2 problems you missed, and rest early.

Tip: after each problem, write one sentence about the pattern you used."""

_EXAM_PLAN = """\
Here is a simple exam preparation plan:

1. List every topic that could appear on the exam and mark each one: confident, okay, or weak.
2. Spend most of your time on the weak topics, in focused 45-minute sessions with 10-minute breaks.
3. After each session, test yourself with practice questions instead of re-reading notes.
4. Two days before the exam, take a full timed practice test.
5. The day before, only review summaries and get a good night's sleep.

Tell me the exam date and how many hours you can study each day, and I can make the plan more precise."""

_LANGUAGE_PLAN = """\
Here is a starter plan for learning a language (30-45 minutes per day):

Week 1: Learn the alphabet or sounds and 50 of the most common words.
Week 2: Learn basic sentence patterns and practice greetings and introductions.
Week 3: Listen to slow beginner audio daily and repeat what you hear.
Week 4: Hold a short conversation with a partner or tutor and review your mistakes.

Tip: short daily practice beats one long session per week."""

_GENERAL_PLAN = """\
Here is a general way to turn your goal into a study plan:

1. Define a clear finish line: what should you be able to do when you are done?
2. Split the goal into 4-6 smaller topics and order them from basic to advanced.
3. Give each topic one or two study sessions of 30-60 minutes.
4. End each week with a short review and one small practice task.
5. Keep one buffer day per week so a missed day does not break your plan.

Tell me how much time you have and your current level, and I can make this more specific."""


def get_mock_reply(message: str) -> str:
    """Return a predefined study-plan reply, picked by simple keyword matching."""
    text = message.lower()

    if any(word in text for word in ("interview", "leetcode", "coding")):
        plan = _INTERVIEW_PLAN
    elif any(word in text for word in ("exam", "test", "midterm", "final")):
        plan = _EXAM_PLAN
    elif any(word in text for word in ("language", "spanish", "french", "japanese", "english")):
        plan = _LANGUAGE_PLAN
    else:
        plan = _GENERAL_PLAN

    return plan + _FOOTER
