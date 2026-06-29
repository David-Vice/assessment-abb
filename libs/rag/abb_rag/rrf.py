from collections.abc import Sequence

RRF_K = 60


def reciprocal_rank_fusion(rankings: Sequence[Sequence[int]], k: int = RRF_K) -> dict[int, float]:
    """Fuse ranked id lists into one score map (higher = better).

    Reciprocal Rank Fusion combines dense and sparse retrieval without score
    normalization: each list contributes 1/(k + rank) per item. Robust and
    parameter-light — the standard choice for hybrid search.
    """

    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return scores
