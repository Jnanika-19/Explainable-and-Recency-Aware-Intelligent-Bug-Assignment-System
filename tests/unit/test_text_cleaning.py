from preprocessing.feature_preparation.text import clean_report_text


def test_text_cleanup_removes_markup_and_normalizes_spacing():
    assert clean_report_text("<p>Fix&nbsp;   crash</p>") == "Fix crash"
