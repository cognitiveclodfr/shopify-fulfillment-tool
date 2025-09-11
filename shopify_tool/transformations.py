"""
This module contains functions for transforming the orders DataFrame before
the main analysis is run. This includes processes like decoding set/bundle
SKUs into their component parts and adding packaging items based on rules.
"""
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def apply_set_decoding(orders_df, decoding_rules):
    """
    Expands set/bundle SKUs into their component SKUs in the orders DataFrame.

    Args:
        orders_df (pd.DataFrame): The DataFrame of order line items.
        decoding_rules (list[dict]): A list of rules for decoding sets.
            Each rule should have a 'set_sku' and a 'components' dict.
            e.g., {'set_sku': 'SET_1', 'components': {'ITEM_A': 1, 'ITEM_B': 2}}

    Returns:
        pd.DataFrame: The transformed DataFrame with sets expanded.
    """
    if not decoding_rules:
        return orders_df

    # Create a lookup dictionary for faster access
    rules_lookup = {}
    for rule in decoding_rules:
        if 'set_sku' in rule and 'components' in rule:
            rules_lookup[rule['set_sku']] = rule['components']

    if not rules_lookup:
        return orders_df

    logger.info(f"Applying set decoding for SKUs: {list(rules_lookup.keys())}")

    new_rows = []
    rows_to_drop = []

    for index, order_row in orders_df.iterrows():
        sku = order_row.get('SKU')
        if sku in rules_lookup:
            rows_to_drop.append(index)
            set_quantity = order_row.get('Quantity', 1)
            components = rules_lookup[sku]

            for component_sku, quantity_in_set in components.items():
                new_row = order_row.to_dict()
                new_row['SKU'] = component_sku
                new_row['Quantity'] = quantity_in_set * set_quantity
                # Add a note to indicate this was part of a set
                original_note = new_row.get('Notes', '')
                if pd.isna(original_note):
                    original_note = ''
                new_row['Notes'] = f"{original_note} (from set {sku})".strip()
                new_rows.append(new_row)

    if not new_rows:
        return orders_df

    # Drop the original set rows
    transformed_df = orders_df.drop(rows_to_drop)

    # Add the new component rows
    new_rows_df = pd.DataFrame(new_rows)

    # Ensure the columns match the original dataframe to prevent issues
    new_rows_df = new_rows_df.reindex(columns=transformed_df.columns)

    result_df = pd.concat([transformed_df, new_rows_df], ignore_index=True)

    logger.info(
        f"Set decoding complete. Dropped {len(rows_to_drop)} set rows and "
        f"added {len(new_rows)} component rows."
    )

    return result_df


def apply_packaging_rules(orders_df, packaging_rules):
    """
    Adds packaging SKUs to orders based on a set of rules.

    Args:
        orders_df (pd.DataFrame): The DataFrame of order line items.
        packaging_rules (list[dict]): A list of rules for adding packaging.
            Each rule has 'conditions' and an 'action' to add a specific SKU.

    Returns:
        pd.DataFrame: The transformed DataFrame with packaging items added.
    """
    if not packaging_rules:
        return orders_df

    logger.info(f"Applying {len(packaging_rules)} packaging rule(s).")

    # To evaluate rules on a per-order basis, we need some per-order attributes.
    # For now, we only support Order_Type (Single/Multi).
    # This requires pre-calculating the item count for each order.
    if 'Order_Number' not in orders_df.columns:
        logger.warning("Cannot apply packaging rules without 'Order_Number' column.")
        return orders_df

    order_item_counts = orders_df.groupby("Order_Number").size().rename("item_count")
    orders_df_with_counts = pd.merge(orders_df, order_item_counts, on="Order_Number", how="left")
    orders_df_with_counts["Order_Type"] = "Single"
    orders_df_with_counts.loc[orders_df_with_counts["item_count"] > 1, "Order_Type"] = "Multi"


    new_rows = []
    # We need to iterate over orders, not rows, to apply rules once per order.
    unique_orders = orders_df_with_counts.drop_duplicates(subset=["Order_Number"])

    for _, order_row in unique_orders.iterrows():
        for rule in packaging_rules:
            if _conditions_met(order_row, rule.get("conditions", [])):
                action = rule.get("action")
                if action and action.get("type") == "ADD_PACKAGING_ITEM":
                    new_row_base = order_row.to_dict()
                    # Clean up the new row to be a generic item
                    for col in ['SKU', 'Quantity', 'Product_Name', 'Notes']: # and other item-specific cols
                        if col in new_row_base:
                            new_row_base[col] = None

                    new_row_base['SKU'] = action.get("sku")
                    new_row_base['Quantity'] = action.get("quantity", 1)
                    new_row_base['Notes'] = "Packaging"
                    new_rows.append(new_row_base)
                    # Stop after first matching rule for this order
                    break

    if not new_rows:
        return orders_df # Return original df if no changes

    new_rows_df = pd.DataFrame(new_rows)
    result_df = pd.concat([orders_df, new_rows_df], ignore_index=True)

    logger.info(f"Packaging rules applied. Added {len(new_rows)} packaging items.")

    return result_df


def _conditions_met(order_row, conditions):
    """
    Checks if a given order row meets all the specified conditions.
    NOTE: This is a simplified implementation for the packaging rule use case.
    It currently only supports '==' on pre-calculated fields like 'Order_Type'.
    """
    if not conditions:
        return True # No conditions means the rule always applies

    for cond in conditions:
        field = cond.get("field")
        operator = cond.get("operator")
        value = cond.get("value")

        if field not in order_row or operator != "==":
            # For now, we only support simple equality checks
            return False

        if order_row[field] != value:
            return False # Condition not met

    return True # All conditions were met
