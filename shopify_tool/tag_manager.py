"""Tag management utilities for Internal_Tags column."""

import json
from typing import List, Optional, Dict
import pandas as pd


def parse_tags(tags_value) -> List[str]:
    """
    Parse Internal_Tags value to list.

    Args:
        tags_value: String, list, or NaN

    Returns:
        List of tag strings
    """
    if pd.isna(tags_value) or tags_value == "":
        return []

    if isinstance(tags_value, list):
        return tags_value

    if isinstance(tags_value, str):
        try:
            # Try parsing as JSON
            parsed = json.loads(tags_value)
            if isinstance(parsed, list):
                return [str(t) for t in parsed]
        except json.JSONDecodeError:
            pass

    return []


def serialize_tags(tags: List[str]) -> str:
    """
    Serialize tag list to JSON string.

    Args:
        tags: List of tag strings

    Returns:
        JSON string representation
    """
    if not tags:
        return "[]"

    # Remove duplicates while preserving order
    unique_tags = []
    for tag in tags:
        if tag not in unique_tags:
            unique_tags.append(tag)

    return json.dumps(unique_tags)


def add_tag(current_tags_value, new_tag: str) -> str:
    """
    Add tag to existing tags (prevents duplicates).

    Args:
        current_tags_value: Current Internal_Tags value
        new_tag: Tag to add

    Returns:
        Updated JSON string
    """
    tags = parse_tags(current_tags_value)

    if new_tag not in tags:
        tags.append(new_tag)

    return serialize_tags(tags)


def remove_tag(current_tags_value, tag_to_remove: str) -> str:
    """
    Remove tag from existing tags.

    Args:
        current_tags_value: Current Internal_Tags value
        tag_to_remove: Tag to remove

    Returns:
        Updated JSON string
    """
    tags = parse_tags(current_tags_value)

    if tag_to_remove in tags:
        tags.remove(tag_to_remove)

    return serialize_tags(tags)


def has_tag(tags_value, tag: str) -> bool:
    """Check if tags contain specific tag."""
    tags = parse_tags(tags_value)
    return tag in tags


def get_tag_category(tag: str, tag_categories: Dict) -> Optional[str]:
    """
    Determine category of a tag.

    Args:
        tag: Tag string
        tag_categories: Config dict with tag categories

    Returns:
        Category name or "custom" if not found
    """
    for category, config in tag_categories.items():
        if tag in config.get("tags", []):
            return category

    return "custom"


def get_tag_color(tag: str, tag_categories: Dict) -> str:
    """
    Get display color for a tag.

    Args:
        tag: Tag string
        tag_categories: Config dict with tag categories

    Returns:
        Hex color code
    """
    category = get_tag_category(tag, tag_categories)
    return tag_categories.get(category, {}).get("color", "#9E9E9E")
