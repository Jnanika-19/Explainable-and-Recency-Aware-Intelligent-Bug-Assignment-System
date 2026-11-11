"""Text and metadata feature preparation for developer recommendation."""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


TEXT_COLUMNS = ("title", "description")
CATEGORICAL_COLUMNS = ("product", "component", "severity", "priority")


def make_feature_preprocessor() -> ColumnTransformer:
    """Create a train-fitted transformer; empty/absent metadata is handled upstream."""
    text = Pipeline([
        ("impute", SimpleImputer(strategy="constant", fill_value="")),
        ("flatten", _TextColumnCombiner()),
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=30000)),
    ])
    categorical = Pipeline([
        ("impute", SimpleImputer(strategy="constant", fill_value="Unknown")),
        ("encode", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("text", text, list(TEXT_COLUMNS)),
        ("metadata", categorical, list(CATEGORICAL_COLUMNS)),
    ], remainder="drop", sparse_threshold=1.0)


class _TextColumnCombiner(BaseEstimator, TransformerMixin):
    """Combine title and description columns into one document per bug."""

    def fit(self, values, y=None):
        return self

    def transform(self, values):
        return [" ".join(str(part) for part in row if part) for row in values]

    def get_feature_names_out(self, input_features=None):
        return ["combined_bug_text"]
