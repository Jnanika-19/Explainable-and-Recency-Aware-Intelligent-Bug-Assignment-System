"""Leakage-aware TF-IDF retrieval over bugs visible before a cutoff."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LogisticRegression


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Timestamps must include a timezone")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class BugDocument:
    bug_id: str
    created_at: datetime
    text: str
    text_available_at: datetime


@dataclass(frozen=True)
class SimilarityMatch:
    bug_id: str
    similarity: float
    created_at: datetime
    relationship_type: str


@dataclass(frozen=True)
class DuplicateTrainingPair:
    """A target label kept separate from point-in-time-safe model features."""

    query_bug_id: str
    candidate_bug_id: str
    candidate_created_at: datetime
    prediction_cutoff: datetime
    similarity: float
    duplicate_label: int

    def __post_init__(self) -> None:
        if not self.query_bug_id or not self.candidate_bug_id:
            raise ValueError("Bug IDs are required")
        if self.query_bug_id == self.candidate_bug_id:
            raise ValueError("A bug cannot be its own candidate")
        if _utc(self.candidate_created_at) >= _utc(self.prediction_cutoff):
            raise ValueError("Candidate bug must predate the prediction cutoff")
        if not isfinite(self.similarity) or not 0 <= self.similarity <= 1:
            raise ValueError("Similarity must be finite and within [0, 1]")
        if self.duplicate_label not in (0, 1):
            raise ValueError("duplicate_label must be binary 0/1")

    def model_features(self) -> dict[str, float]:
        return {"tfidf_cosine_similarity": self.similarity}

    def target(self) -> int:
        return self.duplicate_label


@dataclass(frozen=True)
class RelationshipTrainingPair:
    """A labeled target separate from strictly pre-cutoff similarity features."""

    query_bug_id: str
    candidate_bug_id: str
    candidate_created_at: datetime
    prediction_cutoff: datetime
    similarity: float
    relationship_label: str

    def __post_init__(self) -> None:
        if not self.query_bug_id or not self.candidate_bug_id:
            raise ValueError("Bug IDs are required")
        if self.query_bug_id == self.candidate_bug_id:
            raise ValueError("A bug cannot be its own candidate")
        if _utc(self.candidate_created_at) >= _utc(self.prediction_cutoff):
            raise ValueError("Candidate bug must predate the prediction cutoff")
        if not isfinite(self.similarity) or not 0 <= self.similarity <= 1:
            raise ValueError("Similarity must be finite and within [0, 1]")
        if self.relationship_label not in {"duplicate", "related", "unrelated"}:
            raise ValueError("Unsupported relationship target label")

    def model_features(self) -> dict[str, float]:
        return {"tfidf_cosine_similarity": self.similarity}

    def target(self) -> str:
        return self.relationship_label


class BugRelationshipClassifier:
    """Small reusable baseline; must be fit only on training-split labels."""

    def __init__(self) -> None:
        self._model: LogisticRegression | None = None

    def fit(
        self,
        training_pairs: list[RelationshipTrainingPair],
    ) -> "BugRelationshipClassifier":
        if len(training_pairs) < 4:
            raise ValueError("At least four labeled training pairs are required")
        pair_keys = [
            tuple(sorted((pair.query_bug_id, pair.candidate_bug_id)))
            for pair in training_pairs
        ]
        if len(pair_keys) != len(set(pair_keys)):
            raise ValueError("Training bug pairs must be unique")
        labels = [pair.target() for pair in training_pairs]
        if len(set(labels)) < 2:
            raise ValueError("Training requires at least two relationship classes")
        features = [
            [pair.model_features()["tfidf_cosine_similarity"]]
            for pair in training_pairs
        ]
        model = LogisticRegression(max_iter=1000)
        model.fit(features, labels)
        self._model = model
        return self

    def predict(self, similarity: float) -> tuple[str, dict[str, float]]:
        if self._model is None:
            raise RuntimeError("Relationship classifier must be fit first")
        if not isfinite(similarity) or not 0 <= similarity <= 1:
            raise ValueError("Similarity must be finite and within [0, 1]")
        probabilities = self._model.predict_proba([[similarity]])[0]
        labels = self._model.classes_
        probability_by_label = {
            str(label): float(probability)
            for label, probability in zip(labels, probabilities)
        }
        predicted = str(self._model.predict([[similarity]])[0])
        return predicted, probability_by_label


class PointInTimeBugRetriever:
    def __init__(self) -> None:
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._documents: tuple[BugDocument, ...] = ()
        self.cutoff: datetime | None = None
        self._query_bug_id: str | None = None

    def fit(
        self,
        documents: list[BugDocument],
        *,
        cutoff: datetime,
        query_bug_id: str,
    ) -> "PointInTimeBugRetriever":
        if not query_bug_id:
            raise ValueError("query_bug_id is required")
        point = _utc(cutoff)
        seen: set[str] = set()
        eligible: list[BugDocument] = []
        for document in documents:
            if not document.bug_id or document.bug_id in seen:
                raise ValueError("Historical bug IDs must be nonempty and unique")
            seen.add(document.bug_id)
            if not isinstance(document.text, str):
                raise ValueError("Bug text must be a string")
            created_at = _utc(document.created_at)
            text_available_at = _utc(document.text_available_at)
            if text_available_at < created_at:
                raise ValueError("Bug text cannot be available before bug creation")
            if (
                created_at < point
                and text_available_at < point
                and document.bug_id != query_bug_id
                and document.text.strip()
            ):
                eligible.append(document)
        eligible.sort(key=lambda item: (item.created_at, item.bug_id))
        self.cutoff = point
        self._query_bug_id = query_bug_id
        self._documents = tuple(eligible)
        if not eligible:
            self._vectorizer = None
            self._matrix = None
            return self
        self._vectorizer = TfidfVectorizer()
        self._matrix = self._vectorizer.fit_transform(
            document.text for document in eligible
        )
        return self

    def search(
        self,
        *,
        query_bug_id: str,
        query_text: str,
        query_text_available_at: datetime,
        top_k: int = 5,
        relationship_type: str = "related_bug_candidate",
    ) -> tuple[SimilarityMatch, ...]:
        if self.cutoff is None:
            raise RuntimeError("Retriever must be fit with an explicit cutoff")
        if query_bug_id != self._query_bug_id:
            raise ValueError("search query_bug_id must match the fitted query bug")
        if not isinstance(query_text_available_at, datetime):
            raise ValueError("query text availability timestamp is required")
        if _utc(query_text_available_at) >= self.cutoff:
            raise ValueError("query text must be available strictly before cutoff")
        if top_k < 0:
            raise ValueError("top_k must be non-negative")
        if not relationship_type.strip():
            raise ValueError("relationship_type must be nonempty")
        if not query_bug_id or not query_text.strip():
            raise ValueError("query bug ID and text must be nonempty")
        if top_k == 0 or self._vectorizer is None or self._matrix is None:
            return ()
        query = self._vectorizer.transform([query_text])
        similarities = cosine_similarity(query, self._matrix).ravel()
        ranked = sorted(
            zip(self._documents, similarities),
            key=lambda item: (-float(item[1]), item[0].bug_id),
        )
        return tuple(
            SimilarityMatch(
                bug_id=document.bug_id,
                similarity=float(similarity),
                created_at=document.created_at,
                relationship_type=relationship_type,
            )
            for document, similarity in ranked
            if document.bug_id != query_bug_id
        )[:top_k]
