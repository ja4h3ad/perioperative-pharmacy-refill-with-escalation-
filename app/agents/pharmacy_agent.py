# app/agents/pharmacy_agents.py

class PharmacyAgent:
    def handle_drug_name(self, user_input: str, candidates: list):
        """
        RAG + vector search for fuzzy matching to handle ambiguity
        """
        embeddings = self.embed_model.encode(user_input)
        matches = self.formulary_index.similarity_search(
            embeddings,
            top_k=3,
            filter={"active": True}
        )

        # Progressive disclosure pattern to include user interaction
        if max(m.score for m in matches) > 0.95:
            # High confidence - confirm with user
            return self._confirm_single_match(matches[0])
        else:
            # Low confidence - present options
            return self._present_disambiguation_choices(matches)