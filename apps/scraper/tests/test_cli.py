import argparse

import pytest
from abb_scraper.cli import _positive_int


def test_positive_int_accepts_positive() -> None:
    # Arrange & Act & Assert
    assert _positive_int("5") == 5


def test_positive_int_rejects_zero_and_negative() -> None:
    # Arrange & Act & Assert
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_int("0")
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_int("-3")
