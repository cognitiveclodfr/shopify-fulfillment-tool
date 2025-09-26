import pandas as pd
from . import analysis


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
    # Standard operators
    "equals": "_op_equals",
    "does not equal": "_op_not_equals",
    "contains": "_op_contains",
    "does not contain": "_op_not_contains",
    "is greater than": "_op_greater_than",
    "is less than": "_op_less_than",
    "starts with": "_op_starts_with",
    "ends with": "_op_ends_with",
    "is empty": "_op_is_empty",
    "is not empty": "_op_is_not_empty",
    # Order-level list/set operators
    "contains all": "_op_contains_all",
    "contains any": "_op_contains_any",
    "contains only": "_op_contains_only",
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


def _op_starts_with(series_val, rule_val):
    """Returns True where the series string starts with the rule string."""
    return series_val.str.startswith(rule_val, na=False)


def _op_ends_with(series_val, rule_val):
    """Returns True where the series string ends with the rule string."""
    return series_val.str.endswith(rule_val, na=False)


def _op_is_empty(series_val, rule_val):
    """Returns True where the series value is null or an empty string."""
    # For lists/sets, empty means it's a NaN/None or an empty list/set
    if series_val.dtype == 'object' and series_val.apply(lambda x: isinstance(x, (list, set))).any():
        return series_val.isna() | (series_val.str.len() == 0)
    return series_val.isnull() | (series_val == "")


def _op_is_not_empty(series_val, rule_val):
    """Returns True where the series value is not null and not an empty string."""
    # For lists/sets, not empty means it's not NaN/None and has items
    if series_val.dtype == 'object' and series_val.apply(lambda x: isinstance(x, (list, set))).any():
        return series_val.notna() & (series_val.str.len() > 0)
    return series_val.notna() & (series_val != "")


def _op_contains_all(series_val, rule_val):
    """Returns True if the list/set in the series contains all specified items."""
    # rule_val is expected to be a comma-separated string
    required_items = set(item.strip() for item in rule_val.split(','))
    # The series contains sets, so we check for subset
    return series_val.apply(lambda s: isinstance(s, (list, set)) and required_items.issubset(s))


def _op_contains_any(series_val, rule_val):
    """Returns True if the list/set in the series contains any of the specified items."""
    required_items = set(item.strip() for item in rule_val.split(','))
    return series_val.apply(lambda s: isinstance(s, (list, set)) and not required_items.isdisjoint(s))


def _op_contains_only(series_val, rule_val):
    """Returns True if the list/set in the series contains exactly the specified items."""
    required_items = set(item.strip() for item in rule_val.split(','))
    return series_val.apply(lambda s: isinstance(s, (list, set)) and set(s) == required_items)


class RuleEngine:
    """Applies a set of configured rules to a DataFrame of order data."""

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

        The DataFrame is modified in place.

        Args:
            df (pd.DataFrame): The order data DataFrame to process.

        Returns:
            pd.DataFrame: The modified DataFrame.
        """
        if not self.rules or not isinstance(self.rules, list):
            return df

        # Create columns for actions if they don't exist
        self._prepare_df_for_actions(df)

        for rule in self.rules:
            # Get a boolean Series indicating which rows match the conditions
            matches = self._get_matching_rows(df, rule)

            # Apply actions to the matching rows
            if matches.any():
                self._execute_actions(df, matches, rule.get("actions", []))

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
                # All tag actions modify Status_Note
                elif action_type in ["ADD_TAG", "REMOVE_TAG", "REPLACE_TAG", "CLEAR_TAGS", "EXCLUDE_SKU"]:
                    needed_columns.add("Status_Note")

        # Add only the necessary columns if they don't already exist
        if "Priority" in needed_columns and "Priority" not in df.columns:
            df["Priority"] = "Normal"
        if "_is_excluded" in needed_columns and "_is_excluded" not in df.columns:
            df["_is_excluded"] = False
        if "Status_Note" in needed_columns and "Status_Note" not in df.columns:
            df["Status_Note"] = ""

    def _get_matching_rows(self, df, rule):
        """Evaluates a rule's conditions and finds all matching rows.

        Combines the results of each individual condition in a rule using
        either "AND" (all conditions must match) or "OR" (any condition can
        match) logic, as specified by the rule's 'match' property.

        This now supports both item-level and order-level matching.

        Args:
            df (pd.DataFrame): The DataFrame to evaluate.
            rule (dict): The rule dictionary containing the conditions.

        Returns:
            pd.Series[bool]: A boolean Series with the same index as the
                DataFrame, where `True` indicates a row matches the rule's
                conditions.
        """
        match_type = rule.get("match", "ALL").upper()
        conditions = rule.get("conditions", [])
        match_level = rule.get("match_level", "item") # Default to 'item'

        if not conditions:
            return pd.Series([False] * len(df), index=df.index)

        # For order-level matching, we evaluate conditions once per order, then map the results
        # back to all line items belonging to that order.
        if match_level == "order":
            # Create a smaller DataFrame with one row per order to avoid redundant computation
            order_df = df.drop_duplicates(subset=["Order_Number"]).set_index("Order_Number")

            condition_results = []
            for cond in conditions:
                field, op, value = cond.get("field"), cond.get("operator"), cond.get("value")
                if not all([field, op, field in order_df.columns, op in OPERATOR_MAP]):
                    continue
                op_func = globals()[OPERATOR_MAP[op]]
                condition_results.append(op_func(order_df[field], value))

            if not condition_results:
                return pd.Series([False] * len(df), index=df.index)

            # Combine results and get a Series of matching Order_Numbers
            if match_type == "ALL":
                order_matches = pd.concat(condition_results, axis=1).all(axis=1)
            else: # ANY
                order_matches = pd.concat(condition_results, axis=1).any(axis=1)

            # Map the boolean result back to the original df
            matching_order_numbers = order_df[order_matches].index
            return df["Order_Number"].isin(matching_order_numbers)

        # --- Original item-level matching logic ---
        condition_results = []
        for cond in conditions:
            field, op, value = cond.get("field"), cond.get("operator"), cond.get("value")
            if not all([field, op, field in df.columns, op in OPERATOR_MAP]):
                continue
            op_func = globals()[OPERATOR_MAP[op]]
            condition_results.append(op_func(df[field], value))

        if not condition_results:
            return pd.Series([False] * len(df), index=df.index)

        if match_type == "ALL":
            return pd.concat(condition_results, axis=1).all(axis=1)
        else: # ANY
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
        df_to_modify = df.loc[matches].copy()
        if df_to_modify.empty:
            return

        for action in actions:
            action_type = action.get("type", "").upper()
            value = action.get("value")

            if action_type == "ADD_TAG":
                def process_note(note):
                    tags = analysis.parse_tags_from_note(note)
                    tags.add(value)
                    return analysis.rebuild_tags_string(tags)
                df_to_modify["Status_Note"] = df_to_modify["Status_Note"].apply(process_note)

            elif action_type == "REMOVE_TAG":
                def process_note(note):
                    tags = analysis.parse_tags_from_note(note)
                    tags.discard(value)
                    return analysis.rebuild_tags_string(tags)
                df_to_modify["Status_Note"] = df_to_modify["Status_Note"].apply(process_note)

            elif action_type == "REPLACE_TAG":
                if isinstance(value, str) and "," in value:
                    old_tag, new_tag = value.split(",", 1)
                    def process_note(note):
                        tags = analysis.parse_tags_from_note(note)
                        if old_tag in tags:
                            tags.remove(old_tag)
                            tags.add(new_tag)
                        return analysis.rebuild_tags_string(tags)
                    df_to_modify["Status_Note"] = df_to_modify["Status_Note"].apply(process_note)

            elif action_type == "ADD_TAG_TO_ORDER":
                # This action is functionally identical to ADD_TAG because the matching
                # logic already ensures all items for the order are selected.
                # The logic is kept separate for clarity and future extension.
                def process_note(note):
                    tags = analysis.parse_tags_from_note(note)
                    tags.add(value)
                    return analysis.rebuild_tags_string(tags)
                df_to_modify["Status_Note"] = df_to_modify["Status_Note"].apply(process_note)

            elif action_type == "CLEAR_TAGS":
                df_to_modify["Status_Note"] = ""

            elif action_type == "SET_STATUS":
                df_to_modify["Order_Fulfillment_Status"] = value

            elif action_type == "SET_PRIORITY":
                df_to_modify["Priority"] = value

            elif action_type == "EXCLUDE_FROM_REPORT":
                df_to_modify["_is_excluded"] = True

            elif action_type == "EXCLUDE_SKU":
                if "SKU" in df_to_modify.columns and "Quantity" in df_to_modify.columns:
                    sku_to_exclude = value
                    sku_matches = df_to_modify["SKU"] == sku_to_exclude
                    df_to_modify.loc[sku_matches, "Quantity"] = 0

                    def process_note(note):
                        tags = analysis.parse_tags_from_note(note)
                        tags.add("SKU_EXCLUDED")
                        return analysis.rebuild_tags_string(tags)
                    df_to_modify.loc[sku_matches, "Status_Note"] = df_to_modify.loc[sku_matches, "Status_Note"].apply(process_note)

        # Update the original DataFrame with the changes
        df.update(df_to_modify)
