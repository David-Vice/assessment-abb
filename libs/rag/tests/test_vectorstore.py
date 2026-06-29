from abb_rag.vectorstore import to_halfvec


def test_to_halfvec_formats_bracketed_list() -> None:
    # Arrange & Act & Assert
    assert to_halfvec([0.1, -0.2, 3.0]) == "[0.1,-0.2,3.0]"


def test_to_halfvec_emits_parseable_small_values() -> None:
    # Arrange & Act — tiny values; pgvector's halfvec_in parses scientific notation.
    out = to_halfvec([1e-08, 0.5, -0.25])

    # Assert
    assert out.startswith("[") and out.endswith("]")
    assert out.count(",") == 2
    assert "0.5" in out
