
import os
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
    version="1.0.0",
)

KNOWLEDGE_BRAIN_URL = os.getenv(
    "KNOWLEDGE_BRAIN_URL",
    "http://127.0.0.1:8000",
)

# In-memory storage for generated scopes.
# Data resets when the application restarts.
scopes: dict[str, dict] = {}


class ScopeIn(BaseModel):
    transcript: str = Field(min_length=5, max_length=100000)
    previous_requirements: list[dict] = Field(default_factory=list)


class ApproveIn(BaseModel):
    scope_id: str = Field(min_length=1)


def check_knowledge_brain(feature: str) -> dict:
    """Check whether Task 1 contains information about a feature."""
    try:
        response = httpx.post(
            f"{KNOWLEDGE_BRAIN_URL}/ask",
            json={
                "question": (
                    f"Does the business already support {feature}?"
                )
            },
            timeout=5.0,
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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scope")
def create_scope(payload: ScopeIn):
    """Create a draft scope from a meeting transcript."""
    transcript = payload.transcript.strip()

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail="Transcript cannot be empty.",
        )

    requirements = extract_requirements(transcript)

    knowledge_checks = [
        check_knowledge_brain(item["description"])
        for item in requirements
        if item.get("status")
        not in {"removed", "needs_clarification"}
    ]

    estimate = estimate_requirements(requirements)

    changes = compare_scope(
        payload.previous_requirements,
        requirements,
    )

    proposal = build_proposal(
        transcript,
        requirements,
        payload.previous_requirements,
    )

    scope_id = uuid.uuid4().hex

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
            detail="Scope not found.",
        )

    return scopes[scope_id]


@app.post("/approve")
def approve_scope(payload: ApproveIn):
    """Record human approval for an existing draft."""
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
