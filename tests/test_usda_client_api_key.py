"""Tests for data.usda.client's USDA_API_KEY loading guard (.env via python-dotenv)."""
import pytest

from data.usda import client as usda_client


def test_require_api_key_returns_value_when_present():
    assert usda_client._require_api_key("abc123") == "abc123"


def test_require_api_key_raises_clear_error_when_none():
    with pytest.raises(RuntimeError, match="USDA_API_KEY"):
        usda_client._require_api_key(None)


def test_require_api_key_raises_clear_error_when_empty_string():
    with pytest.raises(RuntimeError, match="USDA_API_KEY"):
        usda_client._require_api_key("")


def test_module_level_usda_api_key_is_loaded_from_dotenv_at_import_time():
    """This repo's .env must define a non-empty USDA_API_KEY for this to hold --
    proves load_dotenv() + os.getenv() actually ran and populated the constant."""
    assert usda_client.USDA_API_KEY
