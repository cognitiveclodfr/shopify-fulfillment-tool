#!/usr/bin/env python
"""
Migration script to update existing client configurations with new source_platform mappings.

This script adds the new column mapping structure to existing client configs that don't have it.
"""

import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shopify_tool.profile_manager import ProfileManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_default_source_mappings():
    """Get default source mappings structure."""
    return {
        "source_platform": "woocommerce",  # Default to WooCommerce for existing clients
        "orders_source_mappings": {
            "shopify": {
                "Name": "Name",
                "Lineitem sku": "Lineitem sku",
                "Lineitem name": "Lineitem name",
                "Lineitem quantity": "Lineitem quantity",
                "Shipping Method": "Shipping Method",
                "Shipping Country": "Shipping Country",
                "Tags": "Tags",
                "Notes": "Notes",
                "Total": "Total"
            },
            "woocommerce": {
                "Order ID": "Name",
                "Lineitem sku": "Lineitem sku",
                "Lineitem name": "Lineitem name",
                "Lineitem quantity": "Lineitem quantity",
                "Shipping Method": "Shipping Method",
                "Shipping Country": "Shipping Country",
                "Tags": "Tags",
                "Notes": "Notes",
                "Total": "Total"
            }
        },
        "stock_source_mappings": {
            "default": {
                "Артикул": "Артикул",
                "Име": "Име",
                "Наличност": "Наличност"
            }
        }
    }


def migrate_client_config(profile_manager: ProfileManager, client_id: str, dry_run: bool = False):
    """
    Migrate a single client configuration to add source mappings.

    Args:
        profile_manager: ProfileManager instance
        client_id: Client ID to migrate
        dry_run: If True, only show what would be changed without saving

    Returns:
        bool: True if migration was needed and performed/would be performed
    """
    logger.info(f"Checking CLIENT_{client_id}...")

    config = profile_manager.load_shopify_config(client_id)
    if not config:
        logger.warning(f"  Could not load config for CLIENT_{client_id}")
        return False

    # Check if already has new structure
    column_mappings = config.get("column_mappings", {})

    if "orders_source_mappings" in column_mappings:
        logger.info(f"  ✓ Already has source mappings")
        return False

    # Needs migration
    logger.info(f"  ⚠ Needs migration - adding source mappings")

    # Get default mappings
    default_mappings = get_default_source_mappings()

    # Merge with existing column_mappings
    if "column_mappings" not in config:
        config["column_mappings"] = {}

    config["column_mappings"].update(default_mappings)

    if dry_run:
        logger.info(f"  [DRY RUN] Would update config with:")
        logger.info(f"    - source_platform: {default_mappings['source_platform']}")
        logger.info(f"    - orders_source_mappings: shopify, woocommerce")
        logger.info(f"    - stock_source_mappings: default")
        return True

    # Save updated config
    try:
        success = profile_manager.save_shopify_config(client_id, config)
        if success:
            logger.info(f"  ✓ Migration complete - config saved")
            return True
        else:
            logger.error(f"  ✗ Failed to save config")
            return False
    except Exception as e:
        logger.error(f"  ✗ Error saving config: {e}")
        return False


def main():
    """Main migration function."""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate client configs to add source platform mappings')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--client', type=str, help='Migrate only specific client (e.g., LIDA)')
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Client Configuration Migration Script")
    logger.info("Adding source_platform and column mappings")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("Running in DRY RUN mode - no changes will be saved")

    logger.info("")

    try:
        # Initialize ProfileManager
        profile_manager = ProfileManager()

        if args.client:
            # Migrate specific client
            clients = [args.client.upper()]
        else:
            # Get all clients
            clients = profile_manager.list_clients()

        if not clients:
            logger.warning("No clients found")
            return

        logger.info(f"Found {len(clients)} client(s) to check")
        logger.info("")

        migrated_count = 0
        skipped_count = 0
        error_count = 0

        for client_id in clients:
            try:
                was_migrated = migrate_client_config(profile_manager, client_id, args.dry_run)
                if was_migrated:
                    migrated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                logger.error(f"Error migrating CLIENT_{client_id}: {e}")
                error_count += 1
            logger.info("")

        # Summary
        logger.info("=" * 60)
        logger.info("Migration Summary")
        logger.info("=" * 60)
        logger.info(f"Total clients checked: {len(clients)}")
        logger.info(f"Migrated: {migrated_count}")
        logger.info(f"Already up-to-date: {skipped_count}")
        logger.info(f"Errors: {error_count}")

        if args.dry_run:
            logger.info("")
            logger.info("This was a DRY RUN - no changes were made")
            logger.info("Run without --dry-run to apply changes")

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
