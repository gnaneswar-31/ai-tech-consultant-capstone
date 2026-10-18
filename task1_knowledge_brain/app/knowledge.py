
import json
import re
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "articles.json"

STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were",
    "do", "does", "did", "have", "has", "had",
    "how", "what", "where", "when", "why", "can",
    "could", "would", "should", "please", "tell",
    "me", "about", "my", "i", "to", "for", "in",
    "on", "of", "and", "or", "it", "this", "that",
    "we", "you", "your", "with", "from", "under",
    "already", "platform", "brilliant", "directories",
}

BILLING_TERMS = {
    "billing",
    "payment",
    "payments",
    "method",
    "details",
    "update",
    "card",
    "invoice",
}


def normalize(text: str) -> list[str]:
    """Convert text into lowercase words."""
    return re.findall(r"[a-z0-9]+", text.lower())


class KnowledgeStore:
    def __init__(self, path: Path = DATA_PATH):
        self.path = path
        self.articles: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        """Load articles from the JSON file."""
        if self.path.exists():
            try:
                data = json.loads(
                    self.path.read_text(encoding="utf-8")
                )
                self.articles = data if isinstance(data, list) else []
            except (json.JSONDecodeError, OSError):
                self.articles = []
        else:
            self.articles = []

    def save(self) -> None:
        """Save articles to the JSON file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                self.articles,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def upsert(self, article: dict[str, Any]) -> dict[str, Any]:
        """Insert an article or update it when its URL already exists."""
        existing = next(
            (
                item
                for item in self.articles
                if item.get("url") == article.get("url")
            ),
            None,
        )

        if existing:
            article["id"] = existing.get("id", article.get("id"))
            self.articles[self.articles.index(existing)] = article
        else:
            self.articles.append(article)

        self.save()
        return article

    def delete_by_url(self, url: str) -> bool:
        """Delete an article using its URL."""
        original_count = len(self.articles)

        self.articles = [
            article
            for article in self.articles
            if article.get("url") != url
        ]

        if len(self.articles) == original_count:
            return False

        self.save()
        return True

    def search(
        self,
        question: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """Find relevant articles using title and content matching."""
        question_words = set(normalize(question)) - STOP_WORDS

        if not question_words:
            return []

        billing_question = bool(question_words & BILLING_TERMS)
        scored = []

        for article in self.articles:
            title_words = set(normalize(article.get("title", "")))
            content_words = set(normalize(article.get("content", "")))

            title_matches = question_words & title_words
            content_matches = question_words & content_words

            article_words = title_words | content_words
            billing_article = bool(article_words & BILLING_TERMS)

            score = (
                2 * len(title_matches) + len(content_matches)
            ) / (2 * len(question_words))

            # Standard relevance matching.
            relevant = (
                score >= 0.25
                and bool(title_matches or content_matches)
            )

            # Allow related terms to find relevant billing articles.
            billing_relevant = (
                billing_question and billing_article
            )

            if relevant or billing_relevant:
                scored.append((score, article))

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            article
            for score, article in scored[:limit]
        ]
