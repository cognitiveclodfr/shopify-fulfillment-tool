import pandas as pd


"""Implements a configurable rule engine to process and modify order data.

This module provides a `RuleEngine` class that can apply a series of
user-defined rules to a pandas DataFrame of order data. Rules are defined in a
JSON or dictionary format and can be used to tag orders, change their status,
set priority, and perform other actions based on a set of conditions.

The core components are:
- **Operator Functions**: A set of functions (_op_equals, _op_contains, etc.)
  that perform the actual comparison for rule conditions.
- **OPERATOR_MAP**: A dictionary that maps user-friendly operator names from
  the configuration (e.g., "contains") to their corresponding function.
- **RuleEngine**: A class that takes a list of rule configurations,
  interprets them, and applies the specified actions to the DataFrame rows
  that match the conditions.
"""

# A mapping from user-friendly operator names to internal function names
OPERATOR_MAP = {
    "equals": "_op_equals",
    "does not equal": "_op_not_equals",
    "contains": "_op_contains",
    "does not contain": "_op_not_contains",
    "is greater than": "_op_greater_than",
    "is less than": "_op_less_than",
    "is greater than or equal": "_op_greater_than_or_equal",
    "is less than or equal": "_op_less_than_or_equal",
    "starts with": "_op_starts_with",
    "ends with": "_op_ends_with",
    "is empty": "_op_is_empty",
    "is not empty": "_op_is_not_empty",
}

# --- Operator Implementations ---


def _op_equals(series_val, rule_val):
    """Returns True where the series value equals the rule value."""
    return series_val == rule_val


def _op_not_equals(series_val, rule_val):
    """Returns True where the series value does not equal the rule value."""
    return series_val != rule_val


def _op_contains(series_val, rule_val):
    """Returns True where the series string contains the rule string (case-insensitive)."""
    # Case-insensitive containment check for strings
    return series_val.str.contains(rule_val, case=False, na=False)


def _op_not_contains(series_val, rule_val):
    """Returns True where the series string does not contain the rule string (case-insensitive)."""
    return ~series_val.str.contains(rule_val, case=False, na=False)


def _op_greater_than(series_val, rule_val):
    """Returns True where the series value is greater than the numeric rule value."""
    return pd.to_numeric(series_val, errors="coerce") > float(rule_val)


def _op_less_than(series_val, rule_val):
    """Returns True where the series value is less than the numeric rule value."""
    return pd.to_numeric(series_val, errors="coerce") < float(rule_val)


def _op_greater_than_or_equal(series_val, rule_val):
    """Returns True where the series value is >= numeric rule value."""
    return pd.to_numeric(series_val, errors="coerce") >= float(rule_val)


def _op_less_than_or_equal(series_val, rule_val):
    """Returns True where the series value is <= numeric rule value."""
    return pd.to_numeric(series_val, errors="coerce") <= float(rule_val)


def _op_starts_with(series_val, rule_val):
    """Returns True where the series string starts with the rule string."""
    return series_val.str.startswith(rule_val, na=False)


def _op_ends_with(series_val, rule_val):
    """Returns True where the series string ends with the rule string."""
    return series_val.str.endswith(rule_val, na=False)


def _op_is_empty(series_val, rule_val):
    """Returns True where the series value is null or an empty string."""
    return series_val.isnull() | (series_val == "")


def _op_is_not_empty(series_val, rule_val):
    """Returns True where the series value is not null and not an empty string."""
    return series_val.notna() & (series_val != "")


class RuleEngine:
    """Applies a set of configured rules to a DataFrame of order data."""

    # Define order-level fields and their calculation methods
    ORDER_LEVEL_FIELDS = {
        "item_count": "_calculate_item_count",
        "total_quantity": "_calculate_total_quantity",
        "has_sku": "_check_has_sku",
    }

    def __init__(self, rules_config):
        """Initializes the RuleEngine with a given set of rules.

        Args:
            rules_config (list[dict]): A list of dictionaries, where each
                dictionary represents a single rule. A rule consists of
                conditions and actions.
        """
        self.rules = rules_config

    def apply(self, df):
        """Applies all configured rules to the given DataFrame.

        This is the main entry point for the engine. It iterates through each
        rule, finds all rows in the DataFrame that match the rule's conditions,
        and then executes the rule's actions on those matching rows.

        Supports both article-level (row-by-row) and order-level (entire order) rules.

        The DataFrame is modified in place.

        Args:
            df (pd.DataFrame): The order data DataFrame to process.

        Returns:
            pd.DataFrame: The modified DataFrame.
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"[RULE ENGINE] Starting rule application with {len(self.rules) if self.rules else 0} rules")

        if not self.rules or not isinstance(self.rules, list):
            logger.warning("[RULE ENGINE] No rules to apply")
            return df

        # Create columns for actions if they don't exist
        self._prepare_df_for_actions(df)

        # Separate rules by level
        article_rules = [r for r in self.rules if r.get("level", "article") == "article"]
        order_rules = [r for r in self.rules if r.get("level") == "order"]

        logger.info(f"[RULE ENGINE] {len(article_rules)} article-level rules, {len(order_rules)} order-level rules")

        # Apply article-level rules (existing logic)
        for idx, rule in enumerate(article_rules):
            rule_name = rule.get("name", f"Rule #{idx+1}")
            logger.info(f"[RULE ENGINE] Applying article rule: {rule_name}")
            logger.info(f"[RULE ENGINE] Conditions: {rule.get('conditions', [])}")

            # Get a boolean Series indicating which rows match the conditions
            matches = self._get_matching_rows(df, rule)

            matched_count = matches.sum()
            logger.info(f"[RULE ENGINE] {matched_count} rows matched conditions")

            # Apply actions to the matching rows
            if matches.any():
                actions = rule.get("actions", [])
                logger.info(f"[RULE ENGINE] Executing {len(actions)} actions: {actions}")
                self._execute_actions(df, matches, actions)
            else:
                logger.info(f"[RULE ENGINE] No matches, skipping actions")

        # Apply order-level rules (NEW)
        if order_rules and "Order_Number" in df.columns:
            for order_number in df["Order_Number"].unique():
                order_mask = df["Order_Number"] == order_number
                order_df = df[order_mask]

                for rule in order_rules:
                    # Evaluate conditions on entire order
                    matches = self._evaluate_order_conditions(
                        order_df,
                        rule.get("conditions", []),
                        rule.get("match", "ALL")
                    )

                    if matches:
                        # Separate actions by scope:
                        # - ADD_TAG applies to ALL rows (for packing list filtering - don't lose unmarked items)
                        # - ADD_ORDER_TAG, SET_PACKAGING_TAG apply to FIRST row only (for counting)
                        actions = rule.get("actions", [])

                        # Actions that apply to ALL rows in order (for filtering)
                        apply_to_all_actions = []
                        # Actions that apply to FIRST row only (for counting)
                        apply_to_first_actions = []

                        for action in actions:
                            action_type = action.get("type", "").upper()
                            if action_type == "ADD_TAG":
                                # ADD_TAG applies to all rows for packing list filtering
                                # This ensures all items in order are tagged, not just first row
                                apply_to_all_actions.append(action)
                            else:
                                # ADD_ORDER_TAG, SET_PACKAGING_TAG, etc. apply to first row only
                                # This ensures proper counting (one tag = one order/package)
                                apply_to_first_actions.append(action)

                        # Apply to all rows of order
                        if apply_to_all_actions:
                            self._execute_actions(df, order_mask, apply_to_all_actions)

                        # Apply to first row only
                        if apply_to_first_actions:
                            first_row_index = order_df.index[0]
                            first_row_mask = pd.Series(False, index=df.index)
                            first_row_mask[first_row_index] = True
                            self._execute_actions(df, first_row_mask, apply_to_first_actions)

        return df

    def _prepare_df_for_actions(self, df):
        """Ensures the DataFrame has the columns required for rule actions.

        Scans all rules to find out which columns will be modified or created
        by the actions (e.g., 'Priority', 'Status_Note'). If these columns
        do not already exist in the DataFrame, they are created and initialized
        with a default value. This prevents errors when an action tries to
        modify a non-existent column.

        Args:
            df (pd.DataFrame): The DataFrame to prepare.
        """
        # Determine which columns are needed by scanning the actions in all rules
        needed_columns = set()
        for rule in self.rules:
            for action in rule.get("actions", []):
                action_type = action.get("type", "").upper()
                if action_type == "SET_PRIORITY":
                    needed_columns.add("Priority")
                elif action_type == "EXCLUDE_FROM_REPORT":
                    needed_columns.add("_is_excluded")
                elif action_type in ["EXCLUDE_SKU", "ADD_TAG", "ADD_ORDER_TAG"]:
                    needed_columns.add("Status_Note")
                elif action_type == "SET_PACKAGING_TAG":
                    needed_columns.add("Packaging_Tags")
                elif action_type == "ADD_INTERNAL_TAG":
                    needed_columns.add("Internal_Tags")

        # Add only the necessary columns if they don't already exist
        if "Priority" in needed_columns and "Priority" not in df.columns:
            df["Priority"] = "Normal"
        if "_is_excluded" in needed_columns and "_is_excluded" not in df.columns:
            df["_is_excluded"] = False
        if "Status_Note" in needed_columns and "Status_Note" not in df.columns:
            df["Status_Note"] = ""
        if "Packaging_Tags" in needed_columns and "Packaging_Tags" not in df.columns:
            df["Packaging_Tags"] = ""
        if "Internal_Tags" in needed_columns and "Internal_Tags" not in df.columns:
            df["Internal_Tags"] = "[]"

    def _get_matching_rows(self, df, rule):
        """Evaluates a rule's conditions and finds all matching rows.

        Combines the results of each individual condition in a rule using
        either "AND" (all conditions must match) or "OR" (any condition can
        match) logic, as specified by the rule's 'match' property.

        Args:
            df (pd.DataFrame): The DataFrame to evaluate.
            rule (dict): The rule dictionary containing the conditions.

        Returns:
            pd.Series[bool]: A boolean Series with the same index as the
                DataFrame, where `True` indicates a row matches the rule's
                conditions.
        """
        import logging
        logger = logging.getLogger(__name__)

        match_type = rule.get("match", "ALL").upper()
        conditions = rule.get("conditions", [])

        if not conditions:
            logger.warning("[RULE ENGINE] No conditions in rule")
            return pd.Series([False] * len(df), index=df.index)

        # Get a boolean Series for each individual condition
        condition_results = []
        for cond in conditions:
            field = cond.get("field")
            operator = cond.get("operator")
            value = cond.get("value")

            # Skip separator fields (from UI)
            if field and field.startswith("---"):
                logger.info(f"[RULE ENGINE] Skipping separator field: {field}")
                continue

            # Check conditions
            if not field:
                logger.warning(f"[RULE ENGINE] Condition missing field: {cond}")
                continue
            if not operator:
                logger.warning(f"[RULE ENGINE] Condition missing operator: {cond}")
                continue
            if field not in df.columns:
                logger.warning(f"[RULE ENGINE] Field '{field}' not in DataFrame columns: {list(df.columns)}")
                continue
            if operator not in OPERATOR_MAP:
                logger.warning(f"[RULE ENGINE] Operator '{operator}' not in OPERATOR_MAP: {list(OPERATOR_MAP.keys())}")
                continue

            op_func_name = OPERATOR_MAP[operator]
            op_func = globals()[op_func_name]

            logger.info(f"[RULE ENGINE] Evaluating condition: {field} {operator} {value}")
            result = op_func(df[field], value)
            matches_count = result.sum()
            logger.info(f"[RULE ENGINE] Condition matched {matches_count} rows")

            condition_results.append(result)

        if not condition_results:
            logger.warning("[RULE ENGINE] No valid conditions evaluated")
            return pd.Series([False] * len(df), index=df.index)

        # Combine the individual condition results based on the match type
        if match_type == "ALL":
            # ALL (AND logic)
            return pd.concat(condition_results, axis=1).all(axis=1)
        else:
            # ANY (OR logic)
            return pd.concat(condition_results, axis=1).any(axis=1)

    def _execute_actions(self, df, matches, actions):
        """Executes a list of actions on the matching rows of the DataFrame.

        Applies the specified actions (e.g., adding a tag, setting a status)
        to the rows of the DataFrame that are marked as `True` in the `matches`
        Series.

        Args:
            df (pd.DataFrame): The DataFrame to be modified.
            matches (pd.Series[bool]): A boolean Series indicating which rows
                to apply the actions to.
            actions (list[dict]): A list of action dictionaries to execute.
        """
        for action in actions:
            action_type = action.get("type", "").upper()
            value = action.get("value")

            if action_type == "ADD_TAG":
                # Per user feedback, ADD_TAG should modify Status_Note, not Tags
                current_notes = df.loc[matches, "Status_Note"].fillna("").astype(str)

                # Append new tag, handling empty notes and preventing duplicates
                def append_note(note):
                    if value in note.split(", "):
                        return note
                    return f"{note}, {value}" if note else value

                new_notes = current_notes.apply(append_note)
                df.loc[matches, "Status_Note"] = new_notes

            elif action_type == "ADD_ORDER_TAG":
                # Add tag to Status_Note (for order-level tagging)
                current_notes = df.loc[matches, "Status_Note"].fillna("").astype(str)

                def append_note(note):
                    if value in note.split(", "):
                        return note
                    return f"{note}, {value}" if note else value

                new_notes = current_notes.apply(append_note)
                df.loc[matches, "Status_Note"] = new_notes

            elif action_type == "SET_PACKAGING_TAG":
                # Set packaging tag (overwrite existing)
                df.loc[matches, "Packaging_Tags"] = value

            elif action_type == "ADD_INTERNAL_TAG":
                # Add tag to Internal_Tags column using tag_manager
                from shopify_tool.tag_manager import add_tag

                current_tags = df.loc[matches, "Internal_Tags"]
                new_tags = current_tags.apply(lambda t: add_tag(t, value))
                df.loc[matches, "Internal_Tags"] = new_tags

            elif action_type == "SET_STATUS":
                df.loc[matches, "Order_Fulfillment_Status"] = value

            elif action_type == "SET_PRIORITY":
                df.loc[matches, "Priority"] = value

            elif action_type == "EXCLUDE_FROM_REPORT":
                df.loc[matches, "_is_excluded"] = True

            elif action_type == "EXCLUDE_SKU":
                # This is a complex, destructive action.
                # For now, we will just mark it for potential later processing.
                # A full implementation would require re-evaluating the entire order.
                # A simple approach is to set its quantity to 0 and flag it.
                if "SKU" in df.columns and "Quantity" in df.columns:
                    sku_to_exclude = value
                    # We need to find rows that match the rule AND the SKU
                    sku_matches = df["SKU"] == sku_to_exclude
                    final_matches = matches & sku_matches
                    df.loc[final_matches, "Quantity"] = 0
                    df.loc[final_matches, "Status_Note"] = df.loc[final_matches, "Status_Note"] + " SKU_EXCLUDED"

    def _evaluate_order_conditions(self, order_df, conditions, match_type):
        """
        Evaluate conditions on order-level (entire order group).

        Args:
            order_df: DataFrame rows for single order
            conditions: List of condition dicts
            match_type: "ALL" or "ANY"

        Returns:
            bool: True if conditions met
        """
        results = []

        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")

            if not all([field, operator]):
                continue

            # Skip separator fields (from UI)
            if field and field.startswith("---"):
                continue

            # Check if this is an order-level field
            if field in self.ORDER_LEVEL_FIELDS:
                # Calculate order-level metric
                calc_method_name = self.ORDER_LEVEL_FIELDS[field]
                calc_method = getattr(self, calc_method_name)
                field_value = calc_method(order_df, value if field == "has_sku" else None)

                # Apply operator (convert to scalar comparison)
                if field == "has_sku":
                    # For has_sku, the method returns True/False directly
                    # operator is ignored - just use the boolean result
                    result = field_value
                elif operator == "equals":
                    result = (field_value == value)
                elif operator == "does not equal":
                    result = (field_value != value)
                elif operator == "is greater than":
                    result = field_value > float(value)
                elif operator == "is less than":
                    result = field_value < float(value)
                elif operator == "is greater than or equal":
                    result = field_value >= float(value)
                elif operator == "is less than or equal":
                    result = field_value <= float(value)
                else:
                    result = False

            else:
                # Regular article-level field - check if ANY row matches
                if field not in order_df.columns or operator not in OPERATOR_MAP:
                    result = False
                else:
                    op_func = globals()[OPERATOR_MAP[operator]]
                    series_result = op_func(order_df[field], value)
                    result = series_result.any()  # At least one row matches

            results.append(result)

        if not results:
            return False

        # Combine results based on match type
        if match_type == "ALL":
            return all(results)
        else:  # ANY
            return any(results)

    def _calculate_item_count(self, order_df, sku_value=None):
        """Count unique items (rows) in order."""
        return len(order_df)

    def _calculate_total_quantity(self, order_df, sku_value=None):
        """Sum all quantities in order."""
        if "Quantity" in order_df.columns:
            return order_df["Quantity"].sum()
        return 0

    def _check_has_sku(self, order_df, sku_value):
        """Check if order contains specific SKU."""
        if "SKU" in order_df.columns and sku_value:
            return (order_df["SKU"] == sku_value).any()
        return False
