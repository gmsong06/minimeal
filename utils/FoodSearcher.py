import faiss
import numpy as np
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer

class FoodSearcher:
    def __init__(self, foundation_foods, legacy_foods=None, branded_foods=None):
        self.foundation_foods = foundation_foods
        self.legacy_foods = legacy_foods or []
        self.branded_foods = branded_foods or []
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.descriptions = [f["description"] for f in foundation_foods]

        embeddings = self.model.encode(
            self.descriptions,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)

    def get_foundation_foods(self, query, k=5, semantic_k=20):
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        scores, indices = self.index.search(query_embedding, semantic_k)

        candidates = []
        for semantic_score, idx in zip(scores[0], indices[0]):
            desc = self.foundation_foods[idx]["description"]
            fuzzy_score = fuzz.token_set_ratio(query.lower(), desc.lower()) / 100.0
            final_score = 0.7 * float(semantic_score) + 0.3 * fuzzy_score
            candidates.append((final_score, self.foundation_foods[idx]))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [food for _, food in candidates[:k]]
    
    def get_legacy_foods(self, query, k=5, semantic_k=20):
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        scores, indices = self.index.search(query_embedding, semantic_k)

        candidates = []
        for semantic_score, idx in zip(scores[0], indices[0]):
            desc = self.legacy_foods[idx]["description"]
            fuzzy_score = fuzz.token_set_ratio(query.lower(), desc.lower()) / 100.0
            final_score = 0.7 * float(semantic_score) + 0.3 * fuzzy_score
            candidates.append((final_score, self.legacy_foods[idx]))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [food for _, food in candidates[:k]]