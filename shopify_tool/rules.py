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

Architecture Note:
    The rule engine operates in two phases:
    1. EVALUATION: Conditions are evaluated to produce a boolean mask indicating
       which rows match the rule criteria.
    2. EXECUTION: Actions are applied only to the matching rows, modifying the
       DataFrame in place.

    This separation ensures that all conditions are checked before any
    modifications occur, preventing partial rule application.

Known Limitations:
    - EXCLUDE_SKU action is destructive and modifies Quantity directly
    - No undo/redo mechanism for rule application
    - Rules are not validated before execution
    - Missing DataFrame columns cause silent condition skips
    (See CRITICAL_ANALYSIS.md for detailed issues and recommendations)

Example Rule Structure:
    {
        "name": "Prioritize High-Value Orders",
        "match": "ALL",  # or "ANY"
        "conditions": [
            {"field": "Total Price", "operator": "is greater than", "value": "150"},
            {"field": "Shipping_Country", "operator": "equals", "value": "Germany"}
        ],
        "actions": [
            {"type": "SET_PRIORITY", "value": "High"},
            {"type": "ADD_TAG", "value": "VIP"}
        ]
    }
"""

import pandas as pd

# ==============================================================================
# OPERATOR REGISTRY
# ==============================================================================
# Maps user-friendly operator names (used in UI and config) to internal
# function names. This allows the config file to use readable strings like
# "contains" while the engine dynamically looks up and calls the corresponding
# implementation function at runtime using Python's globals() dict.
#
# IMPORTANT: These operator names MUST match exactly with the strings used in
# SettingsWindow.OPERATORS_BY_TYPE. Any mismatch will cause rules to fail
# silently during condition evaluation.
#
# Note: There's a parallel set of operators for report filters ("==", "!=", etc.)
# defined in settings_window_pyside.py. See CRITICAL_ANALYSIS.md Section 1.1
# for consolidation recommendations.
OPERATOR_MAP = {
    "equals": "_op_equals",  # Exact match comparison
    "does not equal": "_op_not_equals",  # Inequality comparison
    "contains": "_op_contains",  # Substring search (case-insensitive)
    "does not contain": "_op_not_contains",  # Inverse substring search
    "is greater than": "_op_greater_than",  # Numeric comparison: >
    "is less than": "_op_less_than",  # Numeric comparison: <
    "starts with": "_op_starts_with",  # Prefix match
    "ends with": "_op_ends_with",  # Suffix match
    "is empty": "_op_is_empty",  # Null or empty string check
    "is not empty": "_op_is_not_empty",  # Non-null and non-empty check
}

# ==============================================================================
# OPERATOR IMPLEMENTATIONS
# ==============================================================================
# These functions implement the comparison logic for rule conditions. Each
# function receives a pandas Series and a value, returning a boolean Series
# indicating which elements match the condition.
#
# Design Pattern: All operators follow the signature:
#   operator(series_val: pd.Series, rule_val: Any) -> pd.Series[bool]
#
# This uniform interface allows dynamic lookup and invocation through
# globals()[op_func_name](series, value) in _get_matching_rows().
#
# Implementation Notes:
#   - Use vectorized pandas operations for performance
#   - Handle NA/NaN values explicitly with na=False parameters
#   - For numeric comparisons, coerce to numeric with errors='coerce'
#   - String comparisons are case-insensitive for user-friendliness


def _op_equals(series_val, rule_val):
    """Exact equality comparison operator.

    Returns True for rows where the Series value exactly matches the rule value.
    Uses pandas' == operator which handles various data types correctly.

    Args:
        series_val (pd.Series): Column values from the DataFrame
        rule_val (Any): Value to compare against (from rule config)

    Returns:
        pd.Series[bool]: Boolean mask of matching rows

    Example:
        df["Order_Status"] == "Pending"  -> [True, False, True, ...]
    """
    return series_val == rule_val


def _op_not_equals(series_val, rule_val):
    """Inequality comparison operator.

    Returns True for rows where the Series value does NOT match the rule value.
    Inverse of _op_equals.

    Args:
        series_val (pd.Series): Column values from the DataFrame
        rule_val (Any): Value to compare against

    Returns:
        pd.Series[bool]: Boolean mask of non-matching rows
    """
    return series_val != rule_val


def _op_contains(series_val, rule_val):
    """Case-insensitive substring containment check.

    Returns True for rows where the Series string contains the rule string
    as a substring, ignoring case. NaN values are treated as False.

    Args:
        series_val (pd.Series): String column values
        rule_val (str): Substring to search for

    Returns:
        pd.Series[bool]: Boolean mask of rows containing the substring

    Example:
        If column contains ["ABC-123", "DEF-456", "ABC-789", None]:
        _op_contains(column, "abc") -> [True, False, True, False]

    Note:
        Uses pandas.Series.str.contains() which is vectorized and efficient
        for large datasets. The na=False parameter ensures NaN values return
        False rather than NaN (which would cause issues in boolean operations).
    """
    # Case-insensitive containment check for strings
    return series_val.str.contains(rule_val, case=False, na=False)


def _op_not_contains(series_val, rule_val):
    """Inverse of _op_contains - checks for absence of substring.

    Returns True for rows where the Series string does NOT contain the rule
    string. Case-insensitive, treats NaN as not containing anything.

    Args:
        series_val (pd.Series): String column values
        rule_val (str): Substring to check for absence

    Returns:
        pd.Series[bool]: Boolean mask of rows NOT containing the substring
    """
    return ~series_val.str.contains(rule_val, case=False, na=False)


def _op_greater_than(series_val, rule_val):
    """Numeric greater-than comparison operator.

    Returns True for rows where the numeric value is greater than the rule value.
    Non-numeric values are coerced to NaN and result in False.

    Args:
        series_val (pd.Series): Numeric (or coercible) column values
        rule_val (str|float): Numeric value to compare against

    Returns:
        pd.Series[bool]: Boolean mask of rows with values > rule_val

    Example:
        If column contains [100, 150, "invalid", 200, None]:
        _op_greater_than(column, "120") -> [False, True, False, True, False]

    Implementation Note:
        pd.to_numeric(errors="coerce") converts non-numeric values to NaN,
        which then compare as False in the > operation. This prevents errors
        when users create rules on mixed-type columns.
    """
    return pd.to_numeric(series_val, errors="coerce") > float(rule_val)


def _op_less_than(series_val, rule_val):
    """Numeric less-than comparison operator.

    Returns True for rows where the numeric value is less than the rule value.
    Non-numeric values are coerced to NaN and result in False.

    Args:
        series_val (pd.Series): Numeric (or coercible) column values
        rule_val (str|float): Numeric value to compare against

    Returns:
        pd.Series[bool]: Boolean mask of rows with values < rule_val
    """
    return pd.to_numeric(series_val, errors="coerce") < float(rule_val)


def _op_starts_with(series_val, rule_val):
    """String prefix matching operator.

    Returns True for rows where the string value starts with the rule string.
    Case-sensitive. NaN values return False.

    Args:
        series_val (pd.Series): String column values
        rule_val (str): Prefix to match

    Returns:
        pd.Series[bool]: Boolean mask of rows starting with the prefix

    Example:
        If column contains ["Order-123", "Order-456", "Invoice-789"]:
        _op_starts_with(column, "Order") -> [True, True, False]
    """
    return series_val.str.startswith(rule_val, na=False)


def _op_ends_with(series_val, rule_val):
    """String suffix matching operator.

    Returns True for rows where the string value ends with the rule string.
    Case-sensitive. NaN values return False.

    Args:
        series_val (pd.Series): String column values
        rule_val (str): Suffix to match

    Returns:
        pd.Series[bool]: Boolean mask of rows ending with the suffix
    """
    return series_val.str.endswith(rule_val, na=False)


def _op_is_empty(series_val, rule_val):
    """Empty/null value checker.

    Returns True for rows that are either NaN/None or empty strings.
    The rule_val parameter is ignored but kept for signature consistency.

    Args:
        series_val (pd.Series): Column values to check
        rule_val (Any): Ignored (required for consistent operator signature)

    Returns:
        pd.Series[bool]: Boolean mask of empty/null rows

    Use Case:
        Useful for finding orders with missing notes, empty tags, or
        incomplete data fields.
    """
    return series_val.isnull() | (series_val == "")


def _op_is_not_empty(series_val, rule_val):
    """Non-empty value checker (inverse of _op_is_empty).

    Returns True for rows that have a value (not NaN/None) and are not
    empty strings. The rule_val parameter is ignored.

    Args:
        series_val (pd.Series): Column values to check
        rule_val (Any): Ignored (required for consistent operator signature)

    Returns:
        pd.Series[bool]: Boolean mask of non-empty rows
    """
    return series_val.notna() & (series_val != "")


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
                elif action_type == "EXCLUDE_SKU":
                    needed_columns.add("Status_Note")
                elif action_type == "ADD_TAG":
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

        This is the EVALUATION phase of rule processing. It combines multiple
        condition results using boolean logic (ALL=AND or ANY=OR) to produce
        a single boolean mask indicating which rows match the rule.

        Algorithm:
            1. Extract conditions list from rule
            2. For each condition:
               a. Validate field exists and operator is valid
               b. Look up operator function from OPERATOR_MAP
               c. Execute operator function to get boolean Series
               d. Append to condition_results list
            3. Combine all condition results using match type logic:
               - ALL (AND): Row must match EVERY condition
               - ANY (OR): Row must match AT LEAST ONE condition
            4. Return final boolean mask

        Args:
            df (pd.DataFrame): The DataFrame to evaluate against the rule's
                conditions. Must contain the columns referenced in the rule.
            rule (dict): Rule configuration with structure:
                {
                    "match": "ALL"|"ANY",  # Combination logic
                    "conditions": [
                        {"field": str, "operator": str, "value": any}
                    ]
                }

        Returns:
            pd.Series[bool]: Boolean mask with same index as df. True indicates
                the row matches this rule's conditions and should have actions
                applied to it.

        Edge Cases:
            - No conditions: Returns all False (no rows match)
            - All conditions skipped (invalid): Returns all False
            - Missing field: Silently skips condition (see CRITICAL_ANALYSIS.md)
            - Invalid operator: Silently skips condition

        Performance:
            Uses vectorized pandas operations. For n conditions and m rows:
            - Time complexity: O(n * m) where n << m typically
            - Space complexity: O(n * m) for temporary boolean arrays
        """
        match_type = rule.get("match", "ALL").upper()
        conditions = rule.get("conditions", [])

        # Early exit if rule has no conditions
        if not conditions:
            return pd.Series([False] * len(df), index=df.index)

        # ==================================================================
        # Phase 1: Evaluate each condition independently
        # ==================================================================
        # Each condition produces a boolean Series indicating which rows
        # satisfy that specific condition. These are collected in a list
        # for later combination.
        condition_results = []
        for cond in conditions:
            field = cond.get("field")
            operator = cond.get("operator")
            value = cond.get("value")

            # Validate condition components before execution
            # TODO: Add logging for skipped conditions (see CRITICAL_ANALYSIS.md Section 1.4)
            if not all([field, operator, field in df.columns, operator in OPERATOR_MAP]):
                continue  # Skip invalid conditions silently

            # Dynamic operator lookup: converts string name to function
            # Example: "contains" -> "_op_contains" -> globals()["_op_contains"]
            op_func_name = OPERATOR_MAP[operator]
            op_func = globals()[op_func_name]

            # Execute the operator function on the entire column at once (vectorized)
            condition_results.append(op_func(df[field], value))

        # If all conditions were invalid/skipped, no rows match
        if not condition_results:
            return pd.Series([False] * len(df), index=df.index)

        # ==================================================================
        # Phase 2: Combine condition results using boolean logic
        # ==================================================================
        # Concatenate all boolean Series into a DataFrame where:
        # - Each column is one condition's result
        # - Each row represents a DataFrame row
        # Then apply .all() or .any() across columns to combine
        if match_type == "ALL":
            # ALL (AND logic): Every condition must be True
            # Row i matches if condition_results[0][i] AND condition_results[1][i] AND ...
            return pd.concat(condition_results, axis=1).all(axis=1)
        else:
            # ANY (OR logic): At least one condition must be True
            # Row i matches if condition_results[0][i] OR condition_results[1][i] OR ...
            return pd.concat(condition_results, axis=1).any(axis=1)

    def _execute_actions(self, df, matches, actions):
        """Executes a list of actions on the matching rows of the DataFrame.

        This is the EXECUTION phase of rule processing. After rows have been
        identified by _get_matching_rows(), this method applies the configured
        actions to modify those rows in place.

        The DataFrame is modified directly (in place) for performance reasons.
        Actions are executed sequentially in the order they appear in the
        actions list.

        Supported Actions:
            ADD_TAG: Appends a tag to Status_Note column (comma-separated)
            SET_STATUS: Overwrites Order_Fulfillment_Status with a value
            SET_PRIORITY: Sets the Priority column (High/Normal/Low)
            EXCLUDE_FROM_REPORT: Marks row as excluded (hidden from reports)
            EXCLUDE_SKU: Sets quantity to 0 for specific SKU (DESTRUCTIVE!)

        Args:
            df (pd.DataFrame): The DataFrame to modify. Modified in place.
            matches (pd.Series[bool]): Boolean mask indicating which rows to
                modify. Only rows where matches[i]==True are affected.
            actions (list[dict]): List of action configurations, each with:
                {
                    "type": str,  # Action type (see above)
                    "value": any  # Action-specific value
                }

        Side Effects:
            Modifies df in place by:
            - Appending to existing column values (ADD_TAG)
            - Overwriting column values (SET_STATUS, SET_PRIORITY, EXCLUDE_SKU)
            - Setting boolean flags (EXCLUDE_FROM_REPORT)

        Warnings:
            EXCLUDE_SKU action is DESTRUCTIVE and cannot be undone!
            See CRITICAL_ANALYSIS.md Section 1.2 for details and recommended fix.

        Example:
            If matches = [False, True, True, False] for a 4-row DataFrame,
            and action is {"type": "ADD_TAG", "value": "VIP"},
            then only rows 1 and 2 will have "VIP" appended to their Status_Note.
        """
        for action in actions:
            action_type = action.get("type", "").upper()
            value = action.get("value")

            # ==================================================================
            # ACTION: ADD_TAG
            # ==================================================================
            # Appends a tag to the Status_Note column in a comma-separated
            # format. Prevents duplicate tags from being added.
            #
            # Implementation Details:
            #   - Handles NaN values by converting to empty string
            #   - Checks for duplicate before appending
            #   - Uses ", " as separator for human readability
            #   - Modifies only matching rows (df.loc[matches, ...])
            #
            # Historical Note:
            #   Originally modified "Tags" column but changed to "Status_Note"
            #   per user feedback to keep system tags separate from user tags.
            if action_type == "ADD_TAG":
                # Extract current notes for matching rows, replacing NaN with ""
                current_notes = df.loc[matches, "Status_Note"].fillna("").astype(str)

                # Define helper function to append tag without duplication
                def append_note(note):
                    """Appends value to note if not already present."""
                    # Check if value already exists in comma-separated list
                    if value in note.split(", "):
                        return note  # Already exists, don't add again
                    # Append with separator, or just value if note is empty
                    return f"{note}, {value}" if note else value

                # Apply the append function to all matching rows
                new_notes = current_notes.apply(append_note)
                df.loc[matches, "Status_Note"] = new_notes

            # ==================================================================
            # ACTION: SET_STATUS
            # ==================================================================
            # Overwrites the Order_Fulfillment_Status column with a new value.
            # This is a powerful action that can force an order to be fulfillable
            # or not fulfillable, overriding the automatic analysis result.
            #
            # Use Cases:
            #   - Mark certain orders as "On Hold" for manual review
            #   - Automatically mark pre-orders as "Not Fulfillable"
            #   - Create custom statuses like "Awaiting Confirmation"
            #
            # Warning:
            #   This overrides the algorithmic fulfillment status. Use carefully
            #   as it can cause stock calculation mismatches if not coordinated
            #   with the core analysis logic.
            elif action_type == "SET_STATUS":
                df.loc[matches, "Order_Fulfillment_Status"] = value

            # ==================================================================
            # ACTION: SET_PRIORITY
            # ==================================================================
            # Sets the Priority column to categorize orders for packing sequence.
            # Common values: "High", "Normal", "Low"
            #
            # Use Cases:
            #   - Expedite orders from VIP customers
            #   - Prioritize orders with fast shipping methods
            #   - Deprioritize orders with known delays
            elif action_type == "SET_PRIORITY":
                df.loc[matches, "Priority"] = value

            # ==================================================================
            # ACTION: EXCLUDE_FROM_REPORT
            # ==================================================================
            # Marks rows with a hidden flag (_is_excluded) to exclude them from
            # generated reports like packing lists and stock exports.
            #
            # Use Cases:
            #   - Exclude test orders from production reports
            #   - Hide orders that are handled by a separate process
            #   - Temporarily remove problematic orders from workflows
            #
            # Implementation:
            #   Sets a boolean flag column. The report generation functions
            #   (packing_lists.py, stock_export.py) filter out rows where
            #   _is_excluded == True.
            elif action_type == "EXCLUDE_FROM_REPORT":
                df.loc[matches, "_is_excluded"] = True

            # ==================================================================
            # ACTION: EXCLUDE_SKU (CRITICAL - DESTRUCTIVE!)
            # ==================================================================
            # Excludes a specific SKU from fulfillment by setting its quantity
            # to 0 and adding a flag to Status_Note.
            #
            # ⚠️ WARNING - DESTRUCTIVE OPERATION:
            #   This action PERMANENTLY modifies the Quantity column, destroying
            #   the original data. There is NO undo mechanism.
            #
            # Known Issues:
            #   1. Original quantity is lost forever
            #   2. Re-applying rules causes double-modification
            #   3. Appends to Status_Note without checking if already appended
            #   4. No validation that SKU exists before modification
            #   5. Does not recalculate order fulfillment status
            #
            # Recommended Fix:
            #   See CRITICAL_ANALYSIS.md Section 1.2 for non-destructive
            #   implementation using _excluded_skus and _original_quantity columns.
            #
            # Current Implementation:
            #   - Finds rows that match the rule AND have the specified SKU
            #   - Sets their Quantity to 0 (DESTROYS original value!)
            #   - Appends " SKU_EXCLUDED" to Status_Note (may duplicate!)
            #
            # Use Cases (why this action exists):
            #   - Exclude promotional items that are packed separately
            #   - Remove free gifts from certain courier shipments
            #   - Handle SKUs that require special packaging
            elif action_type == "EXCLUDE_SKU":
                # Validate required columns exist
                if "SKU" in df.columns and "Quantity" in df.columns:
                    sku_to_exclude = value

                    # Narrow down to rows that: (1) match the rule, AND (2) have this SKU
                    # This double-filter ensures we only exclude the SKU from matching orders
                    sku_matches = df["SKU"] == sku_to_exclude
                    final_matches = matches & sku_matches

                    # DESTRUCTIVE OPERATION: Set quantity to 0
                    # TODO: Replace with non-destructive approach (see CRITICAL_ANALYSIS.md)
                    df.loc[final_matches, "Quantity"] = 0

                    # Append flag to Status_Note
                    # BUG: This concatenates without checking for duplicates or existing content
                    df.loc[final_matches, "Status_Note"] = (
                        df.loc[final_matches, "Status_Note"] + " SKU_EXCLUDED"
                    )
