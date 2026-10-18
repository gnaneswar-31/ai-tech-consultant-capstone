
import re
import uuid
from typing import Any


FEATURES = {
    "home page": ["home page", "homepage", "landing page"],
    "about page": ["about page", "about us page"],
    "contact form": ["contact form", "enquiry form", "inquiry form"],
    "product display page": ["product display page", "product page"],
    "online payments": ["online payments", "online payment", "payment gateway"],
    "search": ["search feature", "search page", "search"],
    "export CSV": ["export csv", "csv export", "export to csv"],
    "filters": ["filters", "filtering", "filter results"],
    "export button": ["export button"],
    "user login": ["user login", "login page", "sign in"],
    "admin dashboard": ["admin dashboard", "admin panel"],
}
FEATURE_HOURS = {
    "home page": 4,
    "about page": 3,
    "contact form": 6,
    "product display page": 8,
    "online payments": 12,
    "search": 4,
    "export CSV": 5,
    "filters": 4,
    "export button": 2,
    "user login": 6,
    "admin dashboard": 8,
}


def extract_requirements(transcript: str) -> list[dict[str, Any]]:
    text = transcript.lower().strip()

    if not text:
        return []

    # Ignore greetings and small talk when no project request is present.
    small_talk = {
        "hi",
        "hello",
        "good morning",
        "good afternoon",
        "thank you",
        "thanks",
        "how are you",
        "nice to meet you",
    }

    if text.rstrip("!. ") in small_talk:
        return []

    # Split the transcript into sentences so exclusions can be evaluated
    # in the context where each feature is mentioned.
    sentences = [
        sentence.strip()
        for sentence in re.split(r"[.!?\n]+", text)
        if sentence.strip()
    ]

    exclusion_patterns = [
        r"\bnot required\b",
        r"\bnot needed\b",
        r"\bdon't need\b",
        r"\bdo not need\b",
        r"\bno longer want\b",
        r"\bdon't want\b",
        r"\bdo not want\b",
        r"\bnot include\b",
        r"\bexclude\b",
        r"\bremove\b",
        r"\bno need for\b",
    ]

    requirements = []

    for feature, phrases in FEATURES.items():
        matching_sentences = [
            sentence
            for sentence in sentences
            if any(phrase in sentence for phrase in phrases)
        ]

        if not matching_sentences:
            continue

        removed = False

        for sentence in matching_sentences:
            has_exclusion = any(
                re.search(pattern, sentence)
                for pattern in exclusion_patterns
            )

            if not has_exclusion:
                continue

            # Handle statements such as:
            # "Online payments are not required."
            # "We don't need online payments."
            # "Remove online payments."
            #
            # The feature itself must also be mentioned in the sentence.
            if any(phrase in sentence for phrase in phrases):
                removed = True
                break

        requirements.append(
            {
                "id": str(uuid.uuid4()),
                "description": feature,
                "acceptance_criteria": [
                    f"Confirm the expected behavior of {feature} with the client."
                ],
                "status": "removed" if removed else "proposed",
                "assumption": (
                    "Explicitly excluded by the client."
                    if removed
                    else None
                ),
            }
        )

    # If a clear request exists but no known feature matches it,
    # record it for clarification instead of silently ignoring it.
    if not requirements:
        action_words = [
            "need",
            "want",
            "must",
            "should",
            "build",
            "add",
            "create",
            "implement",
            "require",
        ]

        if any(re.search(rf"\b{word}\b", text) for word in action_words):
            requirements.append(
                {
                    "id": str(uuid.uuid4()),
                    "description": transcript.strip(),
                    "acceptance_criteria": [
                        "Confirm the requirement and expected behavior with the client."
                    ],
                    "status": "needs_clarification",
                    "assumption": "A specific feature needs to be identified.",
                }
            )

    return requirements



def estimate_requirements(
    requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    tasks = []
    total_hours = 0
    assumptions = []

    for item in requirements:
        if item.get("status") == "removed":
            continue

        description = item.get("description", "Unspecified task")
        hours = FEATURE_HOURS.get(description, 4)

        task_assumptions = [
            "Initial estimate; a developer must review the effort."
        ]

        tasks.append({
            **item,
            "task": description,
            "hours": hours,
            "estimated_hours": hours,
            "assumptions": task_assumptions,
        })

        total_hours += hours
        assumptions.extend(task_assumptions)

    return {
        "tasks": tasks,
        "requirements": tasks,
        "total_hours": total_hours,
        "warning": "A developer must review these estimates before commitment.",
        "assumptions": assumptions,
    }



def compare_scope(
    previous_requirements: list[dict[str, Any]],
    current_requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare requirements and distinguish removal from silence."""

    previous_map = {
        item.get("description", "").strip().lower(): item
        for item in previous_requirements
        if isinstance(item, dict) and item.get("description")
    }

    current_map = {
        item.get("description", "").strip().lower(): item
        for item in current_requirements
        if isinstance(item, dict) and item.get("description")
    }

    added = []
    removed = []
    unchanged = []
    out_of_scope = []

    for key, item in current_map.items():
        if item.get("status") == "removed":
            removed.append(item)
        elif key not in previous_map:
            added.append(item)
        else:
            unchanged.append(item)

    # Missing from the new transcript does not mean removed.
    for key, item in previous_map.items():
        if key not in current_map:
            out_of_scope.append(item)

    return {
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "out_of_scope": out_of_scope,
    }



def build_proposal(
    transcript: Any,
    requirements: Any = None,
    previous_requirements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a draft proposal using either supported calling style."""

    if isinstance(transcript, list):
        # Test calling style: build_proposal(requirements, estimate)
        actual_requirements = transcript
        estimate = (
            requirements
            if isinstance(requirements, dict)
            else estimate_requirements(actual_requirements)
        )
        actual_transcript = ""
    else:
        # API calling style: build_proposal(transcript, requirements, previous)
        actual_transcript = str(transcript)
        actual_requirements = (
            requirements if isinstance(requirements, list) else []
        )
        estimate = estimate_requirements(actual_requirements)

    previous_requirements = previous_requirements or []

    # Ensure both lists contain dictionaries before comparing them.
    actual_requirements = [
        item for item in actual_requirements if isinstance(item, dict)
    ]
    previous_requirements = [
        item for item in previous_requirements if isinstance(item, dict)
    ]

    return {
        "title": "Draft Project Scope of Work",
        "status": "draft",
        "transcript": actual_transcript,
        "requirements": actual_requirements,
        "tasks": estimate.get("tasks", []),
        "estimated_hours": estimate.get("total_hours", 0),
        "warning": estimate.get(
            "warning",
            "A developer must review these estimates before commitment.",
        ),
        "assumptions": estimate.get("assumptions", []),
        "scope_changes": compare_scope(
            previous_requirements,
            actual_requirements,
        ),
        "approval_required": True,
        "human_approval_required": True,
        "client_message": (
            "This proposal is a draft and requires human approval "
            "before it is shared with the client."
        ),
    }

