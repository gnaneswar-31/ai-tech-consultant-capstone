from fastapi.testclient import TestClient
from app.main import app, store, feedback_log

client = TestClient(app)

def test_health_ok(): assert client.get("/health").status_code == 200
def test_health_has_article_count(): assert "articles" in client.get("/health").json()
def test_known_billing_question_has_citation():
    r=client.post("/ask",json={"question":"How do I update billing payment method?"})
    assert r.status_code == 200 and r.json()["citations"]
def test_password_question():
    r=client.post("/ask",json={"question":"How can I reset my password?"})
    assert "password" in r.json()["answer"].lower()
def test_unknown_question_abstains():
    r=client.post("/ask",json={"question":"What is the refund policy for a custom plan?"})
    assert r.status_code == 200 and r.json()["needs_human"] is True
def test_empty_question_rejected(): assert client.post("/ask",json={"question":""}).status_code == 422
def test_too_short_question_rejected(): assert client.post("/ask",json={"question":"a"}).status_code == 422
def test_missing_question_rejected(): assert client.post("/ask",json={}).status_code == 422
def test_ingest_article():
    r=client.post("/ingest",json={"title":"Test article title","url":"https://example.test/a","content":"This is a sample test article."})
    assert r.status_code == 200
def test_ingested_article_retrievable():
    client.post("/ingest",json={"title":"Purple widget settings","url":"https://example.test/purple","content":"Purple widget settings are available under the account menu."})
    r=client.post("/ask",json={"question":"Where are purple widget settings?"})
    assert r.json()["citations"][0]["url"] == "https://example.test/purple"
def test_upsert_same_url_keeps_one():
    client.post("/ingest",json={"title":"Unique test article","url":"https://example.test/unique","content":"Old content version."})
    client.post("/ingest",json={"title":"Unique test article updated","url":"https://example.test/unique","content":"New content version."})
    assert sum(a["url"]=="https://example.test/unique" for a in store.articles)==1
def test_feedback_unknown_id_404():
    assert client.post("/feedback",json={"article_id":"missing","question":"Why?","correction":"Because."}).status_code == 404
def test_feedback_valid():
    article=store.articles[0]
    r=client.post("/feedback",json={"article_id":article["id"],"question":"How?","correction":"Use the settings page."})
    assert r.status_code == 200 and r.json()["saved"]
def test_feedback_requires_fields(): assert client.post("/feedback",json={"article_id":"x"}).status_code == 422
def test_article_title_min_length():
    assert client.post("/ingest",json={"title":"x","url":"https://example.test/x","content":"long enough content"}).status_code == 422
def test_article_content_min_length():
    assert client.post("/ingest",json={"title":"Long enough title","url":"https://example.test/x","content":"x"}).status_code == 422
def test_article_url_min_length():
    assert client.post("/ingest",json={"title":"Long enough title","url":"x","content":"long enough content"}).status_code == 422
def test_citation_contains_title_and_url():
    r=client.post("/ask",json={"question":"How do I update billing details?"})
    assert {"title","url"} <= set(r.json()["citations"][0])
def test_answer_response_has_human_flag():
    assert "needs_human" in client.post("/ask",json={"question":"reset password"}).json()
def test_store_delete_url():
    store.upsert({"id":"delete-test","title":"Delete me article","url":"https://example.test/delete","content":"Delete me content."})
    assert store.delete_by_url("https://example.test/delete") is True
def test_store_delete_missing_url():
    assert store.delete_by_url("https://example.test/not-present") is False
def test_search_empty_terms(): assert store.search(" !!! ") == []
def test_answer_has_model_used_flag():
    assert "model_used" in client.post("/ask",json={"question":"reset password"}).json()
