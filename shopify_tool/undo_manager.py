"""
Undo Manager for DataFrame Operations

Manages undo history for DataFrame modifications:
- Records operations after execution (stores affected rows before modification)
- Restores previous DataFrame state
- Persists history to operations_history.json
- Clears "future" operations after new action following undo
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

import pandas as pd


class UndoManager:
    """Manages undo history for DataFrame operations.

    Only stores affected rows (not full DataFrame) for memory efficiency.
    Supports single-level undo (can undo last operation only).
    """

    def __init__(self, main_window):
        """Initialize with reference to MainWindow.

        Args:
            main_window: Reference to MainWindow instance
        """
        self.main_window = main_window
        self.log = logging.getLogger(__name__)

        # History structure
        self.operations = []
        self.current_position = 0
        self.max_history = 20

        # Load existing history if available
        self._load_history()

    def record_operation(
        self,
        operation_type: str,
        description: str,
        params: Dict[str, Any],
        affected_rows_before: pd.DataFrame
    ):
        """Record operation AFTER it executes.

        Args:
            operation_type: Type of operation (toggle_status, add_tag, remove_item, remove_order)
            description: Human-readable description
            params: Dict with operation parameters
            affected_rows_before: DataFrame rows before modification
        """
        try:
            # Clear any "future" operations (redo history) when new operation is recorded
            if self.current_position < len(self.operations):
                self.operations = self.operations[:self.current_position]
                self.log.info(f"Cleared {len(self.operations) - self.current_position} future operations")

            # Convert DataFrame to serializable format
            affected_rows_serialized = affected_rows_before.to_dict('records') if not affected_rows_before.empty else []

            # Get current stats for reference
            stats_before = None
            if hasattr(self.main_window, 'analysis_stats') and self.main_window.analysis_stats:
                stats_before = self.main_window.analysis_stats.copy()

            # Create operation record
            operation_id = len(self.operations) + 1
            operation = {
                "id": operation_id,
                "timestamp": datetime.now().isoformat(),
                "type": operation_type,
                "description": description,
                "params": params,
                "affected_rows_before": affected_rows_serialized,
                "stats_before": stats_before
            }

            # Add to history
            self.operations.append(operation)
            self.current_position = len(self.operations)

            # Limit history size
            if len(self.operations) > self.max_history:
                removed = self.operations.pop(0)
                self.current_position -= 1
                self.log.info(f"Removed oldest operation (limit {self.max_history}): {removed['description']}")

            # Save to file
            self._save_history()

            self.log.info(f"Recorded operation #{operation_id}: {description}")

        except Exception as e:
            self.log.error(f"Failed to record operation: {e}", exc_info=True)

    def can_undo(self) -> bool:
        """Check if undo is possible.

        Returns:
            True if there are operations to undo
        """
        return self.current_position > 0 and len(self.operations) > 0

    def get_undo_description(self) -> Optional[str]:
        """Get description of operation that would be undone.

        Returns:
            Description string or None if no undo available
        """
        if self.can_undo():
            return self.operations[self.current_position - 1].get("description", "Unknown operation")
        return None

    def undo(self) -> Tuple[bool, str]:
        """Undo last operation.

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.can_undo():
            return False, "Nothing to undo"

        try:
            # Get operation to undo
            operation = self.operations[self.current_position - 1]
            operation_type = operation["type"]
            params = operation["params"]
            affected_rows_serialized = operation["affected_rows_before"]

            self.log.info(f"Undoing operation: {operation['description']}")

            # Convert serialized rows back to DataFrame
            affected_rows_before = pd.DataFrame(affected_rows_serialized)

            # Perform undo based on operation type
            if operation_type == "toggle_status":
                success = self._undo_toggle_status(params, affected_rows_before)
            elif operation_type == "add_tag":
                success = self._undo_add_tag(params, affected_rows_before)
            elif operation_type == "remove_item":
                success = self._undo_remove_item(params, affected_rows_before)
            elif operation_type == "remove_order":
                success = self._undo_remove_order(params, affected_rows_before)
            else:
                return False, f"Unknown operation type: {operation_type}"

            if success:
                # Move position back
                self.current_position -= 1

                # Restore stats if available
                if operation.get("stats_before"):
                    self.main_window.analysis_stats = operation["stats_before"]

                # Save updated history
                self._save_history()

                return True, f"Undone: {operation['description']}"
            else:
                return False, f"Failed to undo: {operation['description']}"

        except Exception as e:
            self.log.error(f"Undo failed: {e}", exc_info=True)
            return False, f"Undo failed: {str(e)}"

    def _undo_toggle_status(self, params: Dict, affected_rows_before: pd.DataFrame) -> bool:
        """Undo toggle status operation.

        Args:
            params: Operation parameters
            affected_rows_before: Rows before toggle

        Returns:
            True if successful
        """
        try:
            order_number = params["order_number"]

            # Get current DataFrame
            df = self.main_window.analysis_results_df

            # Find rows for this order
            mask = df["Order_Number"].astype(str).str.strip() == str(order_number).strip()

            if not mask.any():
                self.log.warning(f"Order {order_number} not found in DataFrame")
                return False

            # Restore the affected columns from before state
            # Key columns that change: Order_Fulfillment_Status
            df.loc[mask, "Order_Fulfillment_Status"] = affected_rows_before["Order_Fulfillment_Status"].values[0]

            self.main_window.analysis_results_df = df
            self.log.info(f"Restored status for order {order_number}")

            return True

        except Exception as e:
            self.log.error(f"Failed to undo toggle status: {e}", exc_info=True)
            return False

    def _undo_add_tag(self, params: Dict, affected_rows_before: pd.DataFrame) -> bool:
        """Undo add tag operation.

        Args:
            params: Operation parameters
            affected_rows_before: Rows before tag addition

        Returns:
            True if successful
        """
        try:
            order_number = params["order_number"]

            # Get current DataFrame
            df = self.main_window.analysis_results_df

            # Find rows for this order
            mask = df["Order_Number"].astype(str).str.strip() == str(order_number).strip()

            if not mask.any():
                self.log.warning(f"Order {order_number} not found in DataFrame")
                return False

            # Restore Status_Note from before state
            if "Status_Note" in affected_rows_before.columns:
                for idx, original_idx in enumerate(df[mask].index):
                    if idx < len(affected_rows_before):
                        df.loc[original_idx, "Status_Note"] = affected_rows_before.iloc[idx]["Status_Note"]

            self.main_window.analysis_results_df = df
            self.log.info(f"Restored tags for order {order_number}")

            return True

        except Exception as e:
            self.log.error(f"Failed to undo add tag: {e}", exc_info=True)
            return False

    def _undo_remove_item(self, params: Dict, affected_rows_before: pd.DataFrame) -> bool:
        """Undo remove item operation.

        Args:
            params: Operation parameters
            affected_rows_before: Row before removal

        Returns:
            True if successful
        """
        try:
            # Restore the removed row by concatenating it back
            self.main_window.analysis_results_df = pd.concat(
                [self.main_window.analysis_results_df, affected_rows_before],
                ignore_index=True
            )

            order_number = params.get("order_number", "unknown")
            sku = params.get("sku", "unknown")
            self.log.info(f"Restored item {sku} to order {order_number}")

            return True

        except Exception as e:
            self.log.error(f"Failed to undo remove item: {e}", exc_info=True)
            return False

    def _undo_remove_order(self, params: Dict, affected_rows_before: pd.DataFrame) -> bool:
        """Undo remove order operation.

        Args:
            params: Operation parameters
            affected_rows_before: All rows of order before removal

        Returns:
            True if successful
        """
        try:
            # Restore all removed rows by concatenating them back
            self.main_window.analysis_results_df = pd.concat(
                [self.main_window.analysis_results_df, affected_rows_before],
                ignore_index=True
            )

            order_number = params.get("order_number", "unknown")
            self.log.info(f"Restored order {order_number} with {len(affected_rows_before)} items")

            return True

        except Exception as e:
            self.log.error(f"Failed to undo remove order: {e}", exc_info=True)
            return False

    def _get_history_path(self) -> Optional[Path]:
        """Get path to operations_history.json.

        Returns:
            Path object or None if no active session
        """
        if not self.main_window.session_path:
            return None

        session_path = Path(self.main_window.session_path)
        analysis_dir = session_path / "analysis"
        analysis_dir.mkdir(parents=True, exist_ok=True)

        return analysis_dir / "operations_history.json"

    def _save_history(self):
        """Save history to operations_history.json."""
        try:
            history_path = self._get_history_path()

            if not history_path:
                self.log.debug("No active session, skipping history save")
                return

            history_data = {
                "operations": self.operations,
                "current_position": self.current_position,
                "max_history": self.max_history
            }

            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)

            self.log.debug(f"Saved history to {history_path}")

        except Exception as e:
            self.log.error(f"Failed to save history: {e}", exc_info=True)

    def _load_history(self):
        """Load history from operations_history.json."""
        try:
            history_path = self._get_history_path()

            if not history_path or not history_path.exists():
                self.log.debug("No history file found")
                return

            with open(history_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)

            self.operations = history_data.get("operations", [])
            self.current_position = history_data.get("current_position", 0)
            self.max_history = history_data.get("max_history", 20)

            self.log.info(f"Loaded {len(self.operations)} operations from history")

        except json.JSONDecodeError as e:
            self.log.warning(f"Corrupted history file, starting fresh: {e}")
            self.operations = []
            self.current_position = 0
        except Exception as e:
            self.log.error(f"Failed to load history: {e}", exc_info=True)
            self.operations = []
            self.current_position = 0

    def clear_history(self):
        """Clear all undo history."""
        self.operations = []
        self.current_position = 0
        self._save_history()
        self.log.info("Cleared undo history")
