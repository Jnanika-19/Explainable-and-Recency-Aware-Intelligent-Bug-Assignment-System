
from sentence_transformers import SentenceTransformer, util
import torch

# Limit CPU threads for a smoother run on your laptop
torch.set_num_threads(2)

# Sample bug reports
bug_reports = [
    "Application crashes when uploading a large PDF file",
    "The application terminates when attaching a huge document",
    "Login page displays an incorrect password error"
]

print("Loading Sentence-BERT model...")

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

print("Generating embeddings...")

embeddings = model.encode(
    bug_reports,
    convert_to_tensor=True,
    normalize_embeddings=True
)

similarity = util.cos_sim(embeddings, embeddings)

print("\n========== SBERT SIMILARITY RESULTS ==========")

for i in range(len(bug_reports)):
    for j in range(i + 1, len(bug_reports)):
        print(f"\nBug 1: {bug_reports[i]}")
        print(f"Bug 2: {bug_reports[j]}")
        print(f"Similarity: {similarity[i][j].item():.4f}")

print("\nSBERT test completed successfully!")
