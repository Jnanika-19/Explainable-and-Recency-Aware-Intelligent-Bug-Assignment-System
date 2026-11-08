# Bug Similarity Interface

`retrieval/similar_bugs.py` provides a TF-IDF cosine-similarity retrieval baseline over the historical training records. The result format is a list of `{bug_id, developer_id, similarity}` entries. Member 1 can replace this implementation or provide the same fields in the `similar_bugs` input to `ml_model.rank_developers.rank_developers`; external evidence with developer IDs is used in the recommendation blend and included in returned evidence.

The retrieval index is fitted only from the history passed to training and is saved with the model bundle. It does not claim semantic similarity beyond lexical TF-IDF overlap.
