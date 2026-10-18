
import os
import re
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .workflow import (
    extract_requirements,
    estimate_requirements,
    compare_scope,
    build_proposal,
)

app = FastAPI(
    title="AI Tech Consultant - Meeting to Scope",
    version="1.2.0",
)

KNOWLEDGE_BRAIN_URL = os.getenv(
    "KNOWLEDGE_BRAIN_URL",
    "http://127.0.0.1:8000",
)

# Prototype storage. Scopes reset when the server restarts.
scopes: dict[str, dict] = {}


class ScopeIn(BaseModel):
    transcript: str = Field(min_length=5, max_length=100000)
    scope_id: str | None = None
    previous_requirements: list[dict] = Field(default_factory=list)


class ApproveIn(BaseModel):
    scope_id: str = Field(min_length=1)


def check_knowledge_brain(feature: str) -> dict:
    """Retrieve supporting knowledge for a feature."""
    try:
        response = httpx.post(
            f"{KNOWLEDGE_BRAIN_URL}/ask",
            json={"question": f"Does the business already support {feature}?"},
            timeout=10.0,
        )
        response.raise_for_status()
        answer = response.json()

        return {
            "feature": feature,
            "available": True,
            "answer": answer,
            "needs_human_review": answer.get("needs_human", True),
            "citations": answer.get("citations", []),
        }
    except (httpx.HTTPError, ValueError) as exc:
        return {
            "feature": feature,
            "available": False,
            "error": str(exc),
            "needs_human_review": True,
            "citations": [],
        }


def add_missing_features(
    transcript: str,
    requirements: list[dict],
) -> list[dict]:
    """Recognize online booking and payment features."""
    text = transcript.lower()

    feature_patterns = [
        (
            "online booking",
            r"\bonline booking\b|\bbooking feature\b|\bbooking system\b",
        ),
        (
            "payment integration",
            r"\bpayment integration\b|\bintegrate payments\b|\bpayment gateway\b",
        ),
    ]

    existing = {
        re.sub(r"\s+", " ", item.get("description", "").lower()).strip()
        for item in requirements
    }

    for feature, pattern in feature_patterns:
        if re.search(pattern, text) and feature not in existing:
            requirements.append(
                {
                    "id": str(uuid.uuid4()),
                    "description": feature,
                    "acceptance_criteria": [
                        f"Confirm the detailed requirements for {feature} with the client."
                    ],
                    "status": "proposed",
                    "assumption": (
                        "New feature mentioned in the meeting; "
                        "confirm scope and pricing."
                    ),
                }
            )
            existing.add(feature)

    return requirements


def apply_explicit_removals(
    transcript: str,
    requirements: list[dict],
) -> list[dict]:
    """Remove only features named in explicit removal instructions."""
    removal_pattern = re.compile(
        r"\b(?:remove|delete|drop|exclude)\s+(?:the\s+)?"
        r"(?P<feature>[^.!?,;]+)",
        re.IGNORECASE,
    )

    removed_phrases = [
        re.sub(r"\s+", " ", match.group("feature").lower()).strip()
        for match in removal_pattern.finditer(transcript)
    ]

    for item in requirements:
        description = re.sub(
            r"\s+",
            " ",
            item.get("description", "").lower(),
        ).strip()

        if not description:
            continue

        if any(
            description == phrase or description in phrase
            for phrase in removed_phrases
        ):
            item["status"] = "removed"
            item["assumption"] = "Explicitly excluded by the client."

    return requirements


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scope")
def create_scope(payload: ScopeIn):
    """Create a draft scope or update an existing scope."""
    transcript = payload.transcript.strip()

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail="Transcript cannot be empty.",
        )

    original_scope = None

    if payload.scope_id:
        original_scope = scopes.get(payload.scope_id)

        if original_scope is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Previous scope not found. Create the original scope first. "
                    "Scopes reset when the server restarts."
                ),
            )

        previous_requirements = original_scope.get("requirements", [])
        scope_id = payload.scope_id

    else:
        previous_requirements = payload.previous_requirements
        scope_id = uuid.uuid4().hex

    # UPDATE an existing scope by starting with its original requirements.
    if original_scope:
        requirements = [
            dict(item) for item in previous_requirements
        ]

        # Mark only explicitly named features as removed.
        requirements = apply_explicit_removals(
            transcript,
            requirements,
        )

        # Detect supported new features mentioned in the follow-up.
        new_requirements = add_missing_features(
            transcript,
            [],
        )

        existing_descriptions = {
            item.get("description", "").strip().lower()
            for item in requirements
        }

        for item in new_requirements:
            description = item.get("description", "").strip().lower()

            if description and description not in existing_descriptions:
                requirements.append(item)
                existing_descriptions.add(description)

        # Ensure the new features are not accidentally removed by broad
        # matching. Only explicit removal instructions can remove a feature.
        requirements = apply_explicit_removals(
            transcript,
            requirements,
        )

    else:
        # CREATE a new scope from the initial transcript.
        requirements = extract_requirements(transcript)
        requirements = add_missing_features(
            transcript,
            requirements,
        )
        requirements = apply_explicit_removals(
            transcript,
            requirements,
        )

    # Query the Knowledge Brain only for active requirements.
    knowledge_checks = [
        check_knowledge_brain(item["description"])
        for item in requirements
        if item.get("status") not in {
            "removed",
            "needs_clarification",
        }
    ]

    # Recalculate the estimate after applying the scope changes.
    estimate = estimate_requirements(requirements)

    changes = compare_scope(
        previous_requirements,
        requirements,
    )

    proposal = build_proposal(
        transcript,
        requirements,
        previous_requirements,
    )

    # Keep the proposal as a draft until a human approves it.
    proposal["scope_changes"] = changes
    proposal["estimated_hours"] = estimate.get("total_hours", 0)
    proposal["tasks"] = estimate.get("tasks", [])
    proposal["requirements"] = requirements
    proposal["status"] = "draft"
    proposal["approval_required"] = True
    proposal["human_approval_required"] = True
    proposal["client_message"] = (
        "This proposal is a draft and requires human approval "
        "before it is shared with the client."
    )

    result = {
        "scope_id": scope_id,
        "requirements": requirements,
        "estimate": estimate,
        "changes": changes,
        "knowledge_brain_checks": knowledge_checks,
        "proposal": proposal,
        "human_approval_required": True,
        "approved": False,
    }

    scopes[scope_id] = result
    return result


@app.get("/scope/{scope_id}")
def get_scope(scope_id: str):
    """Retrieve a previously generated scope."""
    if scope_id not in scopes:
        raise HTTPException(
            status_code=404,
            detail=(
                "Scope not found. Scopes are stored in memory "
                "and reset on restart."
            ),
        )

    return scopes[scope_id]


@app.post("/approve")
def approve_scope(payload: ApproveIn):
    """Record human approval; this prototype does not send proposals."""
    scope_id = payload.scope_id

    if scope_id not in scopes:
        raise HTTPException(
            status_code=404,
            detail="Scope not found. Create the scope before approving it.",
        )

    scopes[scope_id]["approved"] = True
    scopes[scope_id]["proposal"]["status"] = "approved"

    return {
        "scope_id": scope_id,
        "approved": True,
        "note": (
            "Approval recorded. This prototype does not send "
            "proposals to clients."
        ),
    }
