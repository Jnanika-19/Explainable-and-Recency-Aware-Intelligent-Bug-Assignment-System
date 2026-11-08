import pytest

from preprocessing.data_cleaning.schema import DatasetSchema


def test_schema_requires_mapping_for_required_fields():
    schema = DatasetSchema(columns={"bug_id": "issue"})
    with pytest.raises(ValueError, match="missing required fields"):
        schema.validate(["issue"])


def test_schema_rejects_unknown_source_columns():
    schema = DatasetSchema(columns={
        "bug_id": "issue", "developer_id": "owner", "title": "summary",
        "description": "details",
    })
    with pytest.raises(ValueError, match="not found"):
        schema.validate(["issue", "owner", "summary"])
