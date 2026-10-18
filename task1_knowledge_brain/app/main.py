
import json
import os
import uuid
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from apscheduler.schedulers.background import BackgroundScheduler

from .knowledge import KnowledgeStore

load_dotenv()

app = FastAPI(
    title="AI Tech Consultant - Knowledge Brain",
    version="1.0.0",
)

# --------------------------------------------------
# Configuration and storage
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
FEEDBACK_PATH = DATA_DIR / "feedback.json"

store = KnowledgeStore()
feedback_log: list[dict] = []


def load_feedback() -> None:
    """Load previously saved feedback."""
    global feedback_log

    if FEEDBACK_PATH.exists():
        try:
            data = json.loads(
                FEEDBACK_PATH.read_text(encoding="utf-8")
            )
            feedback_log = data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            feedback_log = []


def save_feedback() -> None:
    """Persist feedback to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FEEDBACK_PATH.write_text(
        json.dumps(feedback_log, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


load_feedback()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv(
    "CLAUDE_MODEL",
    "claude-sonnet-4-5",
)

SITEMAP_URL = (
    "https://support.brilliantdirectories.com/support/sitemap.xml"
)

KNOWLEDGE_ARTICLE_PREFIX = (
    "https://support.brilliantdirectories.com/"
    "support/solutions/articles/"
)


# --------------------------------------------------
# Request models
# --------------------------------------------------

class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class ArticleIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    url: str = Field(min_length=8, max_length=2000)
    content: str = Field(min_length=10, max_length=100000)
    images: list[str] = Field(default_factory=list)


class FeedbackIn(BaseModel):
    article_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=2000)
    correction: str = Field(min_length=1, max_length=10000)


# --------------------------------------------------
# Article extraction
# --------------------------------------------------

def extract_article(url: str) -> dict | None:
    """Extract a title, readable content, and image URLs from an article."""

    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname != "support.brilliantdirectories.com"
        or "/support/solutions/articles/" not in parsed.path
    ):
        return None

    try:
        response = httpx.get(
            url,
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "AI-Tech-Consultant/1.0"},
        )
        response.raise_for_status()

        # Do not follow a redirect to an unrelated domain.
        final_url = urlparse(str(response.url))
        if (
            final_url.scheme != "https"
            or final_url.hostname
            != "support.brilliantdirectories.com"
        ):
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(
            ["script", "style", "nav", "footer", "header", "noscript"]
        ):
            element.decompose()

        title_tag = soup.find("h1") or soup.find("title")
        title = (
            title_tag.get_text(" ", strip=True)
            if title_tag
            else ""
        )

        main_content = (
            soup.find("article")
            or soup.find("main")
            or soup.find(class_="article-content")
            or soup.body
            or soup
        )

        images = []
        for image_tag in main_content.find_all("img"):
            image_url = image_tag.get("src") or image_tag.get("data-src")
            if not image_url:
                continue

            if image_url.startswith("//"):
                image_url = "https:" + image_url
            elif image_url.startswith("/"):
                image_url = (
                    "https://support.brilliantdirectories.com"
                    + image_url
                )

            parsed_image = urlparse(image_url)
            if parsed_image.scheme in {"https", "http"}:
                images.append(image_url)

        content = main_content.get_text(" ", strip=True)

        if not title or len(content) < 50:
            return None

        return {
            "id": str(uuid.uuid4()),
            "title": title,
            "url": str(response.url),
            "content": content[:100000],
            "images": list(dict.fromkeys(images)),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    except (httpx.HTTPError, ValueError):
        return None


# --------------------------------------------------
# Knowledge Brain search and answer generation
# --------------------------------------------------

def create_fallback_answer(
    question: str,
    matches: list[dict],
) -> dict:
    """Return a source-based answer when Claude is unavailable."""

    if not matches:
        if "password" in question.lower():
            answer = (
                "I could not find verified password-reset instructions "
                "in the knowledge base. Please contact a human support "
                "agent for assistance."
            )
        else:
            answer = (
                "I could not find verified information in the knowledge "
                "base. Please contact a human support agent for assistance."
            )

        return {
            "answer": answer,
            "citations": [],
            "needs_human": True,
            "model_used": False,
        }

    best = matches[0]
    content = best.get("content", "").strip()

    # Avoid presenting a full article as if it were a verified short answer.
    answer = (
        f"Relevant information was found in '{best.get('title', 'the article')}'. "
        "Please review the cited source for the exact instructions."
    )

    if content:
        answer += " The source contains information relevant to your question."

    citations = [
        {
            "title": item.get("title", "Untitled article"),
            "url": item.get("url", ""),
        }
        for item in matches
    ]

    return {
        "answer": answer,
        "citations": citations,
        "needs_human": True,
        "model_used": False,
    }


def generate_claude_answer(
    question: str,
    matches: list[dict],
) -> dict | None:
    """Use Claude to answer using retrieved articles only."""

    if not ANTHROPIC_API_KEY or not matches:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY,
        )

        sources = []
        for index, article in enumerate(matches, start=1):
            sources.append(
                f"[Source {index}]\n"
                f"Title: {article.get('title', '')}\n"
                f"URL: {article.get('url', '')}\n"
                f"Content: {article.get('content', '')[:12000]}"
            )

        prompt = (
            "Answer the user's question using only the supplied source "
            "articles. Do not invent features, instructions, or facts. "
            "If the sources do not adequately answer the question, say "
            "that the information could not be verified and recommend "
            "human support. Cite supporting source URLs in your answer.\n\n"
            f"Question: {question}\n\n"
            f"Sources:\n\n{chr(10).join(sources)}"
        )

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=700,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        answer_text = "\n".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()

        if not answer_text:
            return None

        return {
            "answer": answer_text,
            "citations": [
                {
                    "title": item.get("title", "Untitled article"),
                    "url": item.get("url", ""),
                }
                for item in matches
            ],
            # A human can review the answer before it is relied upon.
            "needs_human": True,
            "model_used": True,
        }

    except Exception as exc:
        print(
            "CLAUDE ANSWER FAILED:",
            type(exc).__name__,
            str(exc),
            flush=True,
        )
        return None


# --------------------------------------------------
# API endpoints
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "articles": len(store.articles),
    }


@app.post("/ingest")
def ingest(article: ArticleIn):
    """Insert or update a supplied article."""

    parsed = urlparse(article.url)

    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail="Article URL must be a valid HTTPS URL.",
        )

    data = {
        "id": str(uuid.uuid4()),
        "title": article.title,
        "url": article.url,
        "content": article.content,
        "images": article.images,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    saved = store.upsert(data)
    return {"article": saved}


@app.post("/ask")
def ask(payload: AskIn):
    """Search the knowledge base and return a cited answer."""

    question = payload.question.strip()

    if len(question) < 2:
        raise HTTPException(
            status_code=422,
            detail="Question must contain at least two non-space characters.",
        )

    matches = store.search(question, limit=3)

    if not matches:
        result = create_fallback_answer(question, [])
    else:
        result = generate_claude_answer(question, matches)

        if result is None:
            result = create_fallback_answer(question, matches)

    return result


@app.post("/feedback")
def feedback(payload: FeedbackIn):
    """Save a human correction associated with a known article."""

    article = next(
        (
            item
            for item in store.articles
            if item.get("id") == payload.article_id
        ),
        None,
    )

    if article is None:
        raise HTTPException(
            status_code=404,
            detail="Article ID not found.",
        )

    record = {
        "article_id": payload.article_id,
        "question": payload.question,
        "correction": payload.correction,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    feedback_log.append(record)

    try:
        save_feedback()
    except OSError as exc:
        feedback_log.pop()
        raise HTTPException(
            status_code=500,
            detail="Could not save feedback.",
        ) from exc

    return {
        "saved": True,
        "feedback_count": len(feedback_log),
    }


@app.post("/refresh")
def refresh(
    sitemap_url: str = SITEMAP_URL,
    max_articles: int = 10,
):
    """Refresh a limited batch of articles from the official sitemap."""

    parsed = urlparse(sitemap_url)

    if (
        parsed.scheme != "https"
        or parsed.hostname != "support.brilliantdirectories.com"
        or not parsed.path.endswith("sitemap.xml")
    ):
        raise HTTPException(
            status_code=400,
            detail="Use the official Brilliant Directories support sitemap.",
        )

    if max_articles < 1 or max_articles > 100:
        raise HTTPException(
            status_code=422,
            detail="max_articles must be between 1 and 100.",
        )

    try:
        response = httpx.get(
            sitemap_url,
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": "AI-Tech-Consultant/1.0"},
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Refresh failed: {type(exc).__name__}: {exc}",
        ) from exc

    urls = [
        element.text.strip()
        for element in root.iter()
        if element.tag.endswith("loc") and element.text
    ]

    article_urls = [
        url
        for url in urls
        if (
            urlparse(url).hostname == "support.brilliantdirectories.com"
            and "/support/solutions/articles/" in urlparse(url).path
        )
    ][:max_articles]

    added_or_updated = 0
    skipped = 0

    for url in article_urls:
        article = extract_article(url)

        if article is None:
            skipped += 1
            continue

        store.upsert(article)
        added_or_updated += 1

    return {
        "sitemap_urls_found": len(urls),
        "articles_attempted": len(article_urls),
        "articles_added_or_updated": added_or_updated,
        "pages_skipped": skipped,
        "articles_in_knowledge_base": len(store.articles),
        "message": (
            "Refresh batch finished. Repeat refreshes to process more "
            "articles and review coverage before relying on the knowledge base."
        ),
    }


# --------------------------------------------------
# Daily refresh scheduler
# --------------------------------------------------

scheduler = BackgroundScheduler()


@app.on_event("startup")
def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            refresh,
            trigger="cron",
            hour=2,
            minute=0,
            id="daily_knowledge_refresh",
            replace_existing=True,
            max_instances=1,
        )
        scheduler.start()


@app.on_event("shutdown")
def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
