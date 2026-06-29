from abb_rag.rrf import reciprocal_rank_fusion


def test_rrf_rewards_items_ranked_high_in_multiple_lists() -> None:
    # Arrange — id 1 is near the top of both lists; id 4 appears in only one.
    dense = [1, 2, 3]
    sparse = [3, 1, 4]

    # Act
    scores = reciprocal_rank_fusion([dense, sparse])

    # Assert
    ranked = sorted(scores, key=lambda doc_id: scores[doc_id], reverse=True)
    assert ranked[0] == 1


def test_rrf_includes_every_seen_id() -> None:
    # Arrange & Act
    scores = reciprocal_rank_fusion([[10, 20], [30]])

    # Assert
    assert set(scores) == {10, 20, 30}
