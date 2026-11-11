"""Retrieve historical bug reports that resemble a new report."""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SimilarBugIndex:
    """Small, serializable TF-IDF index over historical title/description text."""

    def fit(self, history):
        self.history = history.reset_index(drop=True).copy()
        documents = _documents(self.history)
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=30000)
        self.matrix = self.vectorizer.fit_transform(documents)
        return self

    def retrieve(self, title: str, description: str, top_k: int = 5) -> list[dict]:
        if not hasattr(self, "matrix") or not len(self.history):
            return []
        query = self.vectorizer.transform([f"{title or ''} {description or ''}"])
        scores = cosine_similarity(query, self.matrix).ravel()
        ordered = scores.argsort()[::-1]
        found = []
        for index in ordered:
            if scores[index] <= 0:
                break
            row = self.history.iloc[index]
            found.append({
                "bug_id": str(row["bug_id"]),
                "developer_id": str(row["developer_id"]),
                "similarity": float(scores[index]),
            })
            if len(found) >= top_k:
                break
        return found


def _documents(frame):
    return [
        f"{row.get('title', '') or ''} {row.get('description', '') or ''}"
        for _, row in frame.iterrows()
    ]
