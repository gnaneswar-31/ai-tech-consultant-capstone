
from fastapi.testclient import TestClient

from app.main import app
from app.workflow import (
    extract_requirements,
    estimate_requirements,
    compare_scope,
    build_proposal,
)

client = TestClient(app)


# 1. Health check

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# 2. Scope API tests

def test_scope_endpoint_success():
    response = client.post(
        "/scope",
        json={"transcript": "We need a search page"},
    )
    assert response.status_code == 200
    assert response.json()["scope_id"]


def test_empty_transcript_rejected():
    response = client.post("/scope", json={"transcript": ""})
    assert response.status_code == 422


def test_missing_transcript_rejected():
    response = client.post("/scope", json={})
    assert response.status_code == 422


def test_scope_contains_knowledge_checks():
    response = client.post(
        "/scope",
        json={"transcript": "We need a search page"},
    )
    assert "knowledge_brain_checks" in response.json()


# 3. Requirement extraction tests

def test_requirement_extraction():
    result = extract_requirements("We need a search page")
    assert len(result) == 1


def test_ignores_small_talk():
    assert extract_requirements("Nice to meet you") == []


def test_vague_requirement_flagged():
    result = extract_requirements("We need to make it better")
    assert result[0]["status"] == "needs_clarification"


def test_clear_requirement_proposed():
    result = extract_requirements("We need an export button")
    assert result[0]["status"] == "proposed"


def test_multiple_requirements():
    result = extract_requirements(
        "Need a search page\n"
        "Need export CSV\n"
        "Need filters"
    )
    assert len(result) == 3


def test_excluded_feature_marked_removed():
    result = extract_requirements(
        "We need a search page. Online payments are not required."
    )
    payment = next(
        item for item in result
        if item["description"] == "online payments"
    )
    assert payment["status"] == "removed"


# 4. Estimation tests

def test_estimate_total_is_sum():
    requirements = extract_requirements(
        "We need search\nWe need export"
    )
    result = estimate_requirements(requirements)

    assert result["total_hours"] == sum(
        task["hours"] for task in result["tasks"]
    )


def test_estimate_has_warning():
    result = estimate_requirements([])
    assert "developer" in result["warning"].lower()


def test_estimate_assumptions_present():
    requirements = extract_requirements("We need search")
    result = estimate_requirements(requirements)

    assert result["tasks"][0]["assumptions"]


def test_removed_requirements_not_estimated():
    requirements = extract_requirements(
        "We need search. Remove online payments."
    )
    result = estimate_requirements(requirements)

    assert all(
        task["description"] != "online payments"
        for task in result["tasks"]
    )


# 5. Proposal tests

def test_proposal_requires_approval():
    requirements = extract_requirements("We need search")
    estimate = estimate_requirements(requirements)

    result = build_proposal(requirements, estimate)

    assert result["approval_required"] is True


def test_proposal_is_draft():
    requirements = extract_requirements("We need search")
    estimate = estimate_requirements(requirements)

    result = build_proposal(requirements, estimate)

    assert result["status"] == "draft"


def test_proposal_requires_human_approval():
    requirements = extract_requirements("We need search")
    result = build_proposal(
        "We need search",
        requirements,
    )

    assert result["human_approval_required"] is True


# 6. Scope change tests

def test_change_detection_added():
    old = []
    new = extract_requirements("We need search")

    result = compare_scope(old, new)

    assert len(result["added"]) == 1


def test_change_detection_removed():
    old = extract_requirements("We need search")
    new = extract_requirements("Remove the search feature")

    result = compare_scope(old, new)

    assert len(result["removed"]) == 1


def test_change_detection_unchanged():
    old = extract_requirements("We need search")

    result = compare_scope(old, old)

    assert len(result["unchanged"]) == 1


def test_change_detection_case_insensitive():
    old = [{"id": "1", "description": "Add Search"}]
    new = [{"id": "2", "description": "ADD SEARCH"}]

    result = compare_scope(old, new)

    assert len(result["unchanged"]) == 1


def test_unmentioned_feature_is_out_of_scope():
    old = [{"description": "product display page"}]

    result = compare_scope(old, [])

    assert len(result["out_of_scope"]) == 1
    assert result["removed"] == []


# 7. Scope response tests

def test_scope_output_has_estimate():
    response = client.post(
        "/scope",
        json={"transcript": "We need a search page"},
    )

    assert "estimate" in response.json()


def test_scope_output_has_proposal():
    response = client.post(
        "/scope",
        json={"transcript": "We need a search page"},
    )

    assert "proposal" in response.json()


def test_scope_marks_human_approval():
    response = client.post(
        "/scope",
        json={"transcript": "We need a search page"},
    )

    assert response.json()["human_approval_required"] is True


# 8. Scope storage tests

def test_created_scope_can_be_retrieved():
    response = client.post(
        "/scope",
        json={"transcript": "We need a search page"},
    )
    scope_id = response.json()["scope_id"]

    retrieved = client.get(f"/scope/{scope_id}")

    assert retrieved.status_code == 200
    assert retrieved.json()["scope_id"] == scope_id


def test_unknown_scope_returns_404():
    response = client.get("/scope/unknown-scope")
    assert response.status_code == 404


# 9. Approval tests

def test_approval_endpoint():
    scope_response = client.post(
        "/scope",
        json={"transcript": "We need a search page"},
    )
    scope_id = scope_response.json()["scope_id"]

    response = client.post(
        "/approve",
        json={"scope_id": scope_id},
    )

    assert response.status_code == 200
    assert response.json()["approved"] is True


def test_approval_does_not_send():
    scope_response = client.post(
        "/scope",
        json={"transcript": "We need a search page"},
    )
    scope_id = scope_response.json()["scope_id"]

    response = client.post(
        "/approve",
        json={"scope_id": scope_id},
    )

    assert response.status_code == 200
    assert "does not send" in response.json()["note"]


def test_approval_missing_id_rejected():
    response = client.post("/approve", json={})
    assert response.status_code == 422


def test_unknown_scope_cannot_be_approved():
    response = client.post(
        "/approve",
        json={"scope_id": "unknown-scope"},
    )

    assert response.status_code == 404


def test_approved_scope_status_is_updated():
    scope_response = client.post(
        "/scope",
        json={"transcript": "We need a search page"},
    )
    scope_id = scope_response.json()["scope_id"]

    client.post("/approve", json={"scope_id": scope_id})

    retrieved = client.get(f"/scope/{scope_id}")

    assert retrieved.json()["approved"] is True
    assert retrieved.json()["proposal"]["status"] == "approved"
