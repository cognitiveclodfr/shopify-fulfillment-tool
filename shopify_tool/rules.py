import pandas as pd

# A mapping from user-friendly operator names to internal function names
OPERATOR_MAP = {
    'equals': '_op_equals',
    'does not equal': '_op_not_equals',
    'contains': '_op_contains',
    'does not contain': '_op_not_contains',
    'is greater than': '_op_greater_than',
    'is less than': '_op_less_than',
    'starts with': '_op_starts_with',
    'ends with': '_op_ends_with',
    'is empty': '_op_is_empty',
    'is not empty': '_op_is_not_empty',
}

# --- Operator Implementations ---

def _op_equals(series_val, rule_val):
    return series_val == rule_val

def _op_not_equals(series_val, rule_val):
    return series_val != rule_val

def _op_contains(series_val, rule_val):
    # Case-insensitive containment check for strings
    return series_val.str.contains(rule_val, case=False, na=False)

def _op_not_contains(series_val, rule_val):
    return ~series_val.str.contains(rule_val, case=False, na=False)

def _op_greater_than(series_val, rule_val):
    return pd.to_numeric(series_val, errors='coerce') > float(rule_val)

def _op_less_than(series_val, rule_val):
    return pd.to_numeric(series_val, errors='coerce') < float(rule_val)

def _op_starts_with(series_val, rule_val):
    return series_val.str.startswith(rule_val, na=False)

def _op_ends_with(series_val, rule_val):
    return series_val.str.endswith(rule_val, na=False)

def _op_is_empty(series_val, rule_val):
    return series_val.isnull() | (series_val == '')

def _op_is_not_empty(series_val, rule_val):
    return series_val.notna() & (series_val != '')


class RuleEngine:
    def __init__(self, rules_config):
        self.rules = rules_config

    def apply(self, df):
        """
        Apply all configured rules to the DataFrame.
        Returns the modified DataFrame.
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
                self._execute_actions(df, matches, rule.get('actions', []))

        return df

    def _prepare_df_for_actions(self, df):
        """Ensure DataFrame has columns required for the actions in the current ruleset."""
        # Determine which columns are needed by scanning the actions in all rules
        needed_columns = set()
        for rule in self.rules:
            for action in rule.get('actions', []):
                action_type = action.get('type', '').upper()
                if action_type == 'SET_PRIORITY':
                    needed_columns.add('Priority')
                elif action_type == 'EXCLUDE_FROM_REPORT':
                    needed_columns.add('_is_excluded')
                elif action_type == 'EXCLUDE_SKU':
                    needed_columns.add('Status_Note')

        # Add only the necessary columns if they don't already exist
        if 'Priority' in needed_columns and 'Priority' not in df.columns:
            df['Priority'] = 'Normal'
        if '_is_excluded' in needed_columns and '_is_excluded' not in df.columns:
            df['_is_excluded'] = False
        if 'Status_Note' in needed_columns and 'Status_Note' not in df.columns:
            df['Status_Note'] = ''

    def _get_matching_rows(self, df, rule):
        """
        Evaluates the conditions of a rule and returns a boolean Series
        of matching rows.
        """
        match_type = rule.get('match', 'ALL').upper()
        conditions = rule.get('conditions', [])

        if not conditions:
            return pd.Series([False] * len(df), index=df.index)

        # Get a boolean Series for each individual condition
        condition_results = []
        for cond in conditions:
            field = cond.get('field')
            operator = cond.get('operator')
            value = cond.get('value')

            if not all([field, operator, field in df.columns, operator in OPERATOR_MAP]):
                continue

            op_func_name = OPERATOR_MAP[operator]
            op_func = globals()[op_func_name]
            condition_results.append(op_func(df[field], value))

        if not condition_results:
            return pd.Series([False] * len(df), index=df.index)

        # Combine the individual condition results based on the match type
        if match_type == 'ALL':
            # ALL (AND logic)
            return pd.concat(condition_results, axis=1).all(axis=1)
        else:
            # ANY (OR logic)
            return pd.concat(condition_results, axis=1).any(axis=1)

    def _execute_actions(self, df, matches, actions):
        """
        Executes a list of actions on the rows of the DataFrame
        indicated by the 'matches' boolean Series.
        """
        for action in actions:
            action_type = action.get('type', '').upper()
            value = action.get('value')

            if action_type == 'ADD_TAG':
                # Append tag, ensuring not to add duplicates
                current_tags = df.loc[matches, 'Tags'].astype(str)
                # Avoids adding 'nan' to tags if the field is empty
                current_tags[current_tags.str.lower() == 'nan'] = ''
                new_tags = current_tags.apply(lambda t: t + f", {value}" if value not in t.split(', ') else t)
                new_tags = new_tags.str.strip(', ')
                df.loc[matches, 'Tags'] = new_tags

            elif action_type == 'SET_STATUS':
                df.loc[matches, 'Order_Fulfillment_Status'] = value

            elif action_type == 'SET_PRIORITY':
                df.loc[matches, 'Priority'] = value

            elif action_type == 'EXCLUDE_FROM_REPORT':
                df.loc[matches, '_is_excluded'] = True

            elif action_type == 'EXCLUDE_SKU':
                # This is a complex, destructive action.
                # For now, we will just mark it for potential later processing.
                # A full implementation would require re-evaluating the entire order.
                # A simple approach is to set its quantity to 0 and flag it.
                if 'SKU' in df.columns and 'Quantity' in df.columns:
                    sku_to_exclude = value
                    # We need to find rows that match the rule AND the SKU
                    sku_matches = (df['SKU'] == sku_to_exclude)
                    final_matches = matches & sku_matches
                    df.loc[final_matches, 'Quantity'] = 0
                    df.loc[final_matches, 'Status_Note'] = df.loc[final_matches, 'Status_Note'] + ' SKU_EXCLUDED'
