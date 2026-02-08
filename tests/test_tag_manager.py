"""Tests for tag_manager module enhancements (v2 support and caching)."""

import json
import pytest
from shopify_tool.tag_manager import (
    parse_tags,
    serialize_tags,
    add_tag,
    remove_tag,
    has_tag,
    get_tag_category,
    get_tag_color,
    get_config_hash,
    get_tag_category_cached,
    get_category_tags,
    validate_tag_categories_v2,
    _normalize_tag_categories,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def tag_categories_v1():
    """V1 format tag categories (current format)."""
    return {
        "packaging": {
            "label": "Packaging",
            "color": "#4CAF50",
            "tags": ["SMALL_BAG", "LARGE_BAG", "BOX"]
        },
        "priority": {
            "label": "Priority",
            "color": "#FF9800",
            "tags": ["URGENT", "HIGH_VALUE"]
        },
        "custom": {
            "label": "Custom",
            "color": "#9E9E9E",
            "tags": []
        }
    }


@pytest.fixture
def tag_categories_v2():
    """V2 format tag categories (new format with versioning)."""
    return {
        "version": 2,
        "categories": {
            "packaging": {
                "label": "Пакетаж",
                "color": "#4CAF50",
                "order": 1,
                "tags": ["SMALL_BAG", "LARGE_BAG", "BOX"],
                "sku_writeoff": {
                    "enabled": True,
                    "mappings": {
                        "BOX": [
                            {"sku": "PKG-BOX-SMALL", "quantity": 1.0}
                        ]
                    }
                }
            },
            "priority": {
                "label": "Пріоритет",
                "color": "#FF9800",
                "order": 2,
                "tags": ["URGENT", "HIGH_VALUE"],
                "sku_writeoff": {
                    "enabled": False,
                    "mappings": {}
                }
            },
            "custom": {
                "label": "Інші",
                "color": "#9E9E9E",
                "order": 999,
                "tags": [],
                "sku_writeoff": {
                    "enabled": False,
                    "mappings": {}
                }
            }
        }
    }


# ============================================================================
# Tests for existing functions (sanity checks)
# ============================================================================


def test_parse_tags_basic():
    """Test parse_tags with various inputs."""
    assert parse_tags('["TAG1", "TAG2"]') == ["TAG1", "TAG2"]
    assert parse_tags("[]") == []
    assert parse_tags("") == []
    assert parse_tags(None) == []
    assert parse_tags(["TAG1", "TAG2"]) == ["TAG1", "TAG2"]


def test_serialize_tags():
    """Test serialize_tags."""
    assert serialize_tags(["TAG1", "TAG2"]) == '["TAG1", "TAG2"]'
    assert serialize_tags([]) == "[]"
    # Test deduplication
    assert serialize_tags(["TAG1", "TAG2", "TAG1"]) == '["TAG1", "TAG2"]'


def test_add_tag():
    """Test add_tag."""
    result = add_tag("[]", "NEW_TAG")
    assert result == '["NEW_TAG"]'

    result = add_tag('["EXISTING"]', "NEW_TAG")
    tags = json.loads(result)
    assert "EXISTING" in tags
    assert "NEW_TAG" in tags

    # Test no duplicate
    result = add_tag('["EXISTING"]', "EXISTING")
    assert result == '["EXISTING"]'


def test_remove_tag():
    """Test remove_tag."""
    result = remove_tag('["TAG1", "TAG2"]', "TAG1")
    assert result == '["TAG2"]'

    result = remove_tag('["TAG1"]', "TAG1")
    assert result == "[]"


def test_has_tag():
    """Test has_tag."""
    assert has_tag('["TAG1", "TAG2"]', "TAG1") is True
    assert has_tag('["TAG1", "TAG2"]', "TAG3") is False
    assert has_tag("[]", "TAG1") is False


# ============================================================================
# Tests for new v2 functions
# ============================================================================


def test_get_config_hash():
    """Test get_config_hash generates consistent hashes."""
    config1 = {"a": 1, "b": 2}
    config2 = {"b": 2, "a": 1}  # Different order

    hash1 = get_config_hash(config1)
    hash2 = get_config_hash(config2)

    # Should be same hash (sorted keys)
    assert hash1 == hash2
    assert len(hash1) == 32  # MD5 hex length


def test_get_config_hash_changes_with_content():
    """Test get_config_hash changes when config changes."""
    config1 = {"a": 1}
    config2 = {"a": 2}

    hash1 = get_config_hash(config1)
    hash2 = get_config_hash(config2)

    assert hash1 != hash2


def test_normalize_tag_categories_v1(tag_categories_v1):
    """Test _normalize_tag_categories with v1 format."""
    result = _normalize_tag_categories(tag_categories_v1)

    # v1 format returns as-is
    assert result == tag_categories_v1
    assert "packaging" in result
    assert result["packaging"]["tags"] == ["SMALL_BAG", "LARGE_BAG", "BOX"]


def test_normalize_tag_categories_v2(tag_categories_v2):
    """Test _normalize_tag_categories with v2 format."""
    result = _normalize_tag_categories(tag_categories_v2)

    # v2 format returns categories only
    assert "version" not in result
    assert "packaging" in result
    assert result["packaging"]["tags"] == ["SMALL_BAG", "LARGE_BAG", "BOX"]


def test_normalize_tag_categories_empty():
    """Test _normalize_tag_categories with empty config."""
    result = _normalize_tag_categories({})
    assert result == {}

    result = _normalize_tag_categories(None)
    assert result == {}


def test_get_tag_category_cached_v1(tag_categories_v1):
    """Test get_tag_category_cached with v1 format."""
    config_hash = get_config_hash(tag_categories_v1)
    config_json = json.dumps(tag_categories_v1)

    assert get_tag_category_cached("BOX", config_hash, config_json) == "packaging"
    assert get_tag_category_cached("URGENT", config_hash, config_json) == "priority"
    assert get_tag_category_cached("UNKNOWN", config_hash, config_json) == "custom"


def test_get_tag_category_cached_v2(tag_categories_v2):
    """Test get_tag_category_cached with v2 format."""
    config_hash = get_config_hash(tag_categories_v2)
    config_json = json.dumps(tag_categories_v2)

    assert get_tag_category_cached("BOX", config_hash, config_json) == "packaging"
    assert get_tag_category_cached("URGENT", config_hash, config_json) == "priority"
    assert get_tag_category_cached("UNKNOWN", config_hash, config_json) == "custom"


def test_get_tag_category_cached_caching():
    """Test that get_tag_category_cached actually caches results."""
    config = {"cat1": {"tags": ["TAG1"]}}
    config_hash = get_config_hash(config)
    config_json = json.dumps(config)

    # Call twice with same parameters
    result1 = get_tag_category_cached("TAG1", config_hash, config_json)
    result2 = get_tag_category_cached("TAG1", config_hash, config_json)

    assert result1 == result2 == "cat1"

    # Cache info should show hits
    cache_info = get_tag_category_cached.cache_info()
    assert cache_info.hits > 0


def test_get_category_tags_v1(tag_categories_v1):
    """Test get_category_tags with v1 format."""
    tags = get_category_tags("packaging", tag_categories_v1)
    assert tags == ["SMALL_BAG", "LARGE_BAG", "BOX"]

    tags = get_category_tags("priority", tag_categories_v1)
    assert tags == ["URGENT", "HIGH_VALUE"]

    tags = get_category_tags("nonexistent", tag_categories_v1)
    assert tags == []


def test_get_category_tags_v2(tag_categories_v2):
    """Test get_category_tags with v2 format."""
    tags = get_category_tags("packaging", tag_categories_v2)
    assert tags == ["SMALL_BAG", "LARGE_BAG", "BOX"]

    tags = get_category_tags("priority", tag_categories_v2)
    assert tags == ["URGENT", "HIGH_VALUE"]

    tags = get_category_tags("nonexistent", tag_categories_v2)
    assert tags == []


# ============================================================================
# Tests for validate_tag_categories_v2
# ============================================================================


def test_validate_tag_categories_v2_valid(tag_categories_v2):
    """Test validate_tag_categories_v2 with valid config."""
    is_valid, errors = validate_tag_categories_v2(tag_categories_v2)

    assert is_valid is True
    assert len(errors) == 0


def test_validate_tag_categories_v2_missing_version():
    """Test validation fails when version is missing."""
    config = {
        "categories": {
            "cat1": {"label": "Cat1", "color": "#000000", "tags": [], "order": 1}
        }
    }

    is_valid, errors = validate_tag_categories_v2(config)

    assert is_valid is False
    assert any("version" in err.lower() for err in errors)


def test_validate_tag_categories_v2_missing_categories():
    """Test validation fails when categories is missing."""
    config = {"version": 2}

    is_valid, errors = validate_tag_categories_v2(config)

    assert is_valid is False
    assert any("categories" in err.lower() for err in errors)


def test_validate_tag_categories_v2_missing_required_fields():
    """Test validation fails when category missing required fields."""
    config = {
        "version": 2,
        "categories": {
            "cat1": {
                "label": "Cat1"
                # Missing: color, tags, order
            }
        }
    }

    is_valid, errors = validate_tag_categories_v2(config)

    assert is_valid is False
    assert any("color" in err for err in errors)
    assert any("tags" in err for err in errors)
    assert any("order" in err for err in errors)


def test_validate_tag_categories_v2_invalid_color():
    """Test validation fails with invalid color format."""
    config = {
        "version": 2,
        "categories": {
            "cat1": {
                "label": "Cat1",
                "color": "red",  # Invalid
                "tags": [],
                "order": 1
            }
        }
    }

    is_valid, errors = validate_tag_categories_v2(config)

    assert is_valid is False
    assert any("color" in err.lower() for err in errors)


def test_validate_tag_categories_v2_duplicate_tags():
    """Test validation fails when tag appears in multiple categories."""
    config = {
        "version": 2,
        "categories": {
            "cat1": {
                "label": "Cat1",
                "color": "#000000",
                "tags": ["TAG1", "TAG2"],
                "order": 1
            },
            "cat2": {
                "label": "Cat2",
                "color": "#111111",
                "tags": ["TAG2", "TAG3"],  # TAG2 duplicate
                "order": 2
            }
        }
    }

    is_valid, errors = validate_tag_categories_v2(config)

    assert is_valid is False
    assert any("duplicate" in err.lower() and "TAG2" in err for err in errors)


def test_validate_tag_categories_v2_invalid_order():
    """Test validation fails when order is not an integer."""
    config = {
        "version": 2,
        "categories": {
            "cat1": {
                "label": "Cat1",
                "color": "#000000",
                "tags": [],
                "order": "1"  # Should be int
            }
        }
    }

    is_valid, errors = validate_tag_categories_v2(config)

    assert is_valid is False
    assert any("order" in err.lower() for err in errors)


def test_validate_tag_categories_v2_sku_writeoff_missing_enabled():
    """Test validation fails when sku_writeoff missing enabled field."""
    config = {
        "version": 2,
        "categories": {
            "cat1": {
                "label": "Cat1",
                "color": "#000000",
                "tags": ["TAG1"],
                "order": 1,
                "sku_writeoff": {
                    # Missing enabled
                    "mappings": {}
                }
            }
        }
    }

    is_valid, errors = validate_tag_categories_v2(config)

    assert is_valid is False
    assert any("enabled" in err.lower() for err in errors)


def test_validate_tag_categories_v2_sku_writeoff_invalid_mapping():
    """Test validation fails with invalid sku_writeoff mapping."""
    config = {
        "version": 2,
        "categories": {
            "cat1": {
                "label": "Cat1",
                "color": "#000000",
                "tags": ["TAG1"],
                "order": 1,
                "sku_writeoff": {
                    "enabled": True,
                    "mappings": {
                        "TAG1": [
                            {
                                "sku": "SKU1"
                                # Missing quantity
                            }
                        ]
                    }
                }
            }
        }
    }

    is_valid, errors = validate_tag_categories_v2(config)

    assert is_valid is False
    assert any("quantity" in err.lower() for err in errors)


def test_validate_tag_categories_v2_sku_writeoff_negative_quantity():
    """Test validation fails with negative quantity."""
    config = {
        "version": 2,
        "categories": {
            "cat1": {
                "label": "Cat1",
                "color": "#000000",
                "tags": ["TAG1"],
                "order": 1,
                "sku_writeoff": {
                    "enabled": True,
                    "mappings": {
                        "TAG1": [
                            {
                                "sku": "SKU1",
                                "quantity": -1  # Invalid
                            }
                        ]
                    }
                }
            }
        }
    }

    is_valid, errors = validate_tag_categories_v2(config)

    assert is_valid is False
    assert any("positive" in err.lower() for err in errors)


def test_validate_tag_categories_v2_sku_writeoff_valid_with_description():
    """Test validation passes with valid sku_writeoff including description."""
    config = {
        "version": 2,
        "categories": {
            "packaging": {
                "label": "Пакетаж",
                "color": "#4CAF50",
                "tags": ["BOX"],
                "order": 1,
                "sku_writeoff": {
                    "enabled": True,
                    "mappings": {
                        "BOX": [
                            {
                                "sku": "PKG-BOX-SMALL",
                                "quantity": 1.0,
                                "description": "Small box"  # Optional field
                            }
                        ]
                    }
                }
            }
        }
    }

    is_valid, errors = validate_tag_categories_v2(config)

    assert is_valid is True
    assert len(errors) == 0


# ============================================================================
# Integration tests
# ============================================================================


def test_backward_compatibility_v1_still_works(tag_categories_v1):
    """Test that old v1 format still works with existing functions."""
    # Existing functions should still work with v1
    assert get_tag_category("BOX", tag_categories_v1) == "packaging"
    assert get_tag_color("BOX", tag_categories_v1) == "#4CAF50"

    # New functions should also work with v1
    tags = get_category_tags("packaging", tag_categories_v1)
    assert "BOX" in tags


def test_forward_compatibility_v2_works_with_old_functions(tag_categories_v2):
    """Test that v2 format needs normalization for old functions."""
    # Old functions expect direct categories dict, not wrapped
    # They won't work directly with v2, but normalized categories should work
    categories = tag_categories_v2["categories"]

    assert get_tag_category("BOX", categories) == "packaging"
    assert get_tag_color("BOX", categories) == "#4CAF50"


def test_cache_invalidation_on_config_change():
    """Test that cache is invalidated when config changes."""
    config1 = {
        "version": 2,
        "categories": {
            "cat1": {"label": "Cat1", "color": "#000000", "tags": ["TAG1"], "order": 1}
        }
    }
    config2 = {
        "version": 2,
        "categories": {
            "cat1": {"label": "Cat1", "color": "#000000", "tags": ["TAG2"], "order": 1}
        }
    }

    hash1 = get_config_hash(config1)
    hash2 = get_config_hash(config2)

    # Different hashes mean cache won't be used
    assert hash1 != hash2

    # Get cached results
    result1 = get_tag_category_cached("TAG1", hash1, json.dumps(config1))
    result2 = get_tag_category_cached("TAG2", hash2, json.dumps(config2))

    assert result1 == "cat1"
    assert result2 == "cat1"
