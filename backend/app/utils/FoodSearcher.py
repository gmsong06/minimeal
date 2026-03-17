import faiss
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer


class FoodSearcher:
    def __init__(self, foundation_foods, legacy_foods=None, branded_foods=None):
        self.foundation_foods = foundation_foods
        self.legacy_foods = legacy_foods or []
        self.branded_foods = branded_foods or []
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.foundation_descriptions = [f["description"] for f in self.foundation_foods]
        self.legacy_descriptions = [f["description"] for f in self.legacy_foods]
        self.foundation_index = self._build_index(self.foundation_descriptions)
        self.legacy_index = self._build_index(self.legacy_descriptions)

    def _build_index(self, descriptions):
        if not descriptions:
            return None

        embeddings = self.model.encode(
            descriptions,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        return index

    def _encode_query(self, query):
        return self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

    def _normalize_query(self, query):
        normalized = query.strip().lower()
        normalized = normalized.replace("-", " ")
        tokens = [token for token in normalized.split() if token]
        return " ".join(tokens)

    def _query_variants(self, query):
        normalized = self._normalize_query(query)
        variants = [normalized]
        replacements = {
            "burger bun": ["hamburger bun", "hamburger roll", "bun", "roll", "bread roll"],
            "hot dog bun": ["frankfurter roll", "bun", "roll", "bread roll"],
            "sub roll": ["hoagie roll", "sandwich roll", "roll", "bread roll"],
            "hero roll": ["sub roll", "sandwich roll", "roll", "bread roll"],
            "bread bowl": ["roll", "bread", "sourdough bread"],
        }

        if normalized in replacements:
            variants.extend(replacements[normalized])

        if " bun" in normalized or normalized.endswith("bun"):
            variants.extend(["hamburger bun", "bun", "roll", "bread roll"])
        if " roll" in normalized or normalized.endswith("roll"):
            variants.extend(["roll", "bread roll", "bun"])
        if " bread" in normalized or normalized.endswith("bread"):
            variants.extend(["bread", "roll"])

        tokens = normalized.split()
        if len(tokens) > 1:
            variants.extend(tokens)
            head = tokens[-1]
            variants.append(head)
            if head in {"bun", "roll", "bread"}:
                variants.append(f"{tokens[0]} {head}")

        deduped = []
        seen = set()
        for variant in variants:
            clean = self._normalize_query(variant)
            if clean and clean not in seen:
                seen.add(clean)
                deduped.append(clean)
        return deduped

    def _important_tokens(self, query):
        stopwords = {
            "and", "with", "of", "the", "a", "an", "style", "plain", "fresh",
            "cooked", "raw", "large", "small",
        }
        return {
            token for token in self._normalize_query(query).split()
            if token not in stopwords
        }

    def _category_bonus(self, query, food):
        query_tokens = self._important_tokens(query)
        category = (
            food.get("foodCategory", {}).get("description", "")
            if isinstance(food.get("foodCategory"), dict)
            else ""
        ).lower()
        description = food.get("description", "").lower()

        bonus = 0.0
        bread_terms = {"bun", "roll", "bread"}
        sauce_terms = {"ketchup", "mustard", "mayo", "sauce", "condiment", "dressing"}
        query_is_bread_like = bool(query_tokens & bread_terms)
        desc_has_bread_term = any(term in description for term in bread_terms)

        if query_is_bread_like:
            if "baked" in category or any(term in description for term in bread_terms):
                bonus += 0.12
            else:
                bonus -= 0.45
            if any(term in description for term in sauce_terms):
                bonus -= 0.18
            if "burger king" in description:
                bonus -= 0.2
            if "hamburger" in description and desc_has_bread_term:
                bonus += 0.12

        return bonus

    def _score_candidate(self, query, semantic_score, food):
        description = food["description"].lower()
        normalized_query = self._normalize_query(query)
        query_tokens = self._important_tokens(query)
        desc_tokens = set(description.replace(",", " ").split())

        token_set = fuzz.token_set_ratio(normalized_query, description) / 100.0
        partial = fuzz.partial_ratio(normalized_query, description) / 100.0
        token_overlap = (
            len(query_tokens & desc_tokens) / max(len(query_tokens), 1)
            if query_tokens else 0.0
        )
        exact_phrase_bonus = 0.1 if normalized_query in description else 0.0
        category_bonus = self._category_bonus(query, food)

        return (
            0.45 * float(semantic_score)
            + 0.25 * token_set
            + 0.15 * partial
            + 0.15 * token_overlap
            + exact_phrase_bonus
            + category_bonus
        )

    def _search_dataset(self, query, foods, index, k, semantic_k):
        if not foods or index is None:
            return []

        scores, indices = index.search(self._encode_query(query), min(semantic_k, len(foods)))

        candidates = []
        for semantic_score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            food = foods[idx]
            final_score = self._score_candidate(query, semantic_score, food)
            candidates.append((final_score, food))
        return candidates

    def _search_with_variants(self, query, foods, index, k=5, semantic_k=20):
        by_fdc_id = {}

        for variant in self._query_variants(query):
            for score, food in self._search_dataset(variant, foods, index, k, semantic_k):
                fdc_id = food.get("fdcId")
                if fdc_id is None:
                    continue

                existing = by_fdc_id.get(fdc_id)
                if existing is None or score > existing[0]:
                    by_fdc_id[fdc_id] = (score, food)

        ranked = sorted(by_fdc_id.values(), key=lambda item: item[0], reverse=True)
        return [food for _, food in ranked[:k]]

    def get_foundation_foods(self, query, k=5, semantic_k=20):
        return self._search_with_variants(
            query,
            self.foundation_foods,
            self.foundation_index,
            k=k,
            semantic_k=semantic_k,
        )

    def get_legacy_foods(self, query, k=5, semantic_k=20):
        return self._search_with_variants(
            query,
            self.legacy_foods,
            self.legacy_index,
            k=k,
            semantic_k=semantic_k,
        )
