"""Unit tests for harness factory."""

import pytest

from app.harnesses.factory import create_harness, get_parser
from app.harnesses.parsers.base import DefaultOutputParser
from app.harnesses.parsers.goose import GooseOutputParser
from app.harnesses.registry import HarnessProfile, harness_registry
from app.harnesses.subprocess_harness import SubprocessHarness


@pytest.fixture(autouse=True)
def _setup_test_harnesses(tmp_path):
    """Seed the registry with test harnesses.

    The root conftest isolates all registries to temp paths automatically.
    """
    harness_registry._config_path = tmp_path / "harnesses.yaml"
    harness_registry._items["test-subprocess"] = HarnessProfile(
        id="test-subprocess", name="Test Subprocess", type="subprocess", binary_path="echo"
    )
    harness_registry._persist_yaml()


def test_create_builtin_type_raises():
    harness_registry._items["test-builtin"] = HarnessProfile(id="test-builtin", name="Test Builtin", type="builtin")
    with pytest.raises(ValueError, match="Unknown harness type"):
        create_harness("test-builtin")


def test_create_subprocess_harness():
    harness = create_harness("test-subprocess")
    assert isinstance(harness, SubprocessHarness)


def test_create_unknown_raises():
    with pytest.raises(ValueError, match="Unknown harness"):
        create_harness("nonexistent-harness")


def test_get_parser_goose():
    parser = get_parser("goose")
    assert isinstance(parser, GooseOutputParser)


def test_get_parser_default():
    parser = get_parser(None)
    assert isinstance(parser, DefaultOutputParser)

    parser2 = get_parser("unknown-format")
    assert isinstance(parser2, DefaultOutputParser)
