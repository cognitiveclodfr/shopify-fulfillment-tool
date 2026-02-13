"""Tests for UndoManager (shopify_tool/undo_manager.py).

Covers:
- record_operation adds to history
- can_undo() returns correct values
- get_undo_description() returns human-readable description
- undo() reverses toggle_status operation
- History size limit enforcement
- Context validation (blocks undo from different session/client)
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from shopify_tool.undo_manager import UndoManager


def make_mock_mw(session_path=None, client_id="TEST_CLIENT"):
    """Create a mock MainWindow with common attributes."""
    mw = Mock()
    mw.session_path = session_path
    mw.current_client_id = client_id
    mw.analysis_stats = None
    mw.analysis_results_df = pd.DataFrame({
        "Order_Number": ["ORD-1", "ORD-1"],
        "SKU": ["A", "B"],
        "Order_Fulfillment_Status": ["Fulfillable", "Fulfillable"],
    })
    return mw


def make_undo_manager(temp_dir=None, session_path=None):
    """Create UndoManager with a mock MainWindow, optionally with a session path."""
    if session_path is None and temp_dir is not None:
        session_path = temp_dir / "test_session"
        session_path.mkdir(parents=True, exist_ok=True)
    mw = make_mock_mw(session_path=session_path)
    with patch.object(UndoManager, '_load_history'):
        um = UndoManager(mw)
    return um, mw


class TestCanUndo:

    def test_false_when_empty(self, temp_dir):
        um, _ = make_undo_manager(temp_dir)
        assert not um.can_undo()

    def test_true_after_record(self, temp_dir):
        um, _ = make_undo_manager(temp_dir)
        with patch.object(um, '_save_history'):
            um.record_operation(
                "toggle_status", "Toggle ORD-1", {"order_number": "ORD-1"},
                pd.DataFrame({"Order_Fulfillment_Status": ["Fulfillable"]})
            )
        assert um.can_undo()


class TestRecordOperation:

    def test_adds_to_operations(self, temp_dir):
        um, _ = make_undo_manager(temp_dir)
        with patch.object(um, '_save_history'):
            um.record_operation(
                "toggle_status", "Toggle ORD-1", {"order_number": "ORD-1"},
                pd.DataFrame({"Order_Fulfillment_Status": ["Fulfillable"]})
            )
        assert len(um.operations) == 1

    def test_stores_correct_type_and_description(self, temp_dir):
        um, _ = make_undo_manager(temp_dir)
        with patch.object(um, '_save_history'):
            um.record_operation(
                "add_tag", "Added tag VIP to ORD-1",
                {"order_number": "ORD-1", "tag": "VIP"},
                pd.DataFrame()
            )
        op = um.operations[0]
        assert op["type"] == "add_tag"
        assert op["description"] == "Added tag VIP to ORD-1"

    def test_clears_future_on_new_record(self, temp_dir):
        um, _ = make_undo_manager(temp_dir)
        with patch.object(um, '_save_history'):
            # Add two operations
            um.record_operation("toggle_status", "op1", {}, pd.DataFrame())
            um.record_operation("toggle_status", "op2", {}, pd.DataFrame())
        assert um.current_position == 2

        # Simulate undo moving position back
        um.current_position = 1

        # Adding a new operation should clear op2
        with patch.object(um, '_save_history'):
            um.record_operation("toggle_status", "op3", {}, pd.DataFrame())
        assert len(um.operations) == 2
        assert um.operations[-1]["description"] == "op3"

    def test_respects_max_history(self, temp_dir):
        um, _ = make_undo_manager(temp_dir)
        um.max_history = 3
        with patch.object(um, '_save_history'):
            for i in range(5):
                um.record_operation("toggle_status", f"op{i}", {}, pd.DataFrame())
        assert len(um.operations) == 3
        # Oldest operations must be dropped first (FIFO trim)
        descriptions = [op["description"] for op in um.operations]
        assert descriptions == ["op2", "op3", "op4"]


class TestGetUndoDescription:

    def test_returns_description(self, temp_dir):
        um, _ = make_undo_manager(temp_dir)
        with patch.object(um, '_save_history'):
            um.record_operation("toggle_status", "Toggle ORD-2", {"order_number": "ORD-2"}, pd.DataFrame())
        assert um.get_undo_description() == "Toggle ORD-2"

    def test_returns_none_when_nothing_to_undo(self, temp_dir):
        um, _ = make_undo_manager(temp_dir)
        assert um.get_undo_description() is None


class TestUndo:

    def test_undo_nothing_returns_false(self, temp_dir):
        um, _ = make_undo_manager(temp_dir)
        success, msg = um.undo()
        assert not success
        assert "Nothing" in msg

    def test_undo_toggle_status_restores_value(self, temp_dir):
        um, mw = make_undo_manager(temp_dir)
        # Set up DataFrame with current (modified) status
        mw.analysis_results_df = pd.DataFrame({
            "Order_Number": ["ORD-1", "ORD-1"],
            "SKU": ["A", "B"],
            "Order_Fulfillment_Status": ["Not Fulfillable", "Not Fulfillable"],
        })

        # Record the state BEFORE the change (was Fulfillable)
        before_rows = pd.DataFrame({"Order_Fulfillment_Status": ["Fulfillable", "Fulfillable"]})
        with patch.object(um, '_save_history'):
            um.record_operation(
                "toggle_status", "Toggle ORD-1",
                {"order_number": "ORD-1"},
                before_rows
            )

        with patch.object(um, '_save_history'):
            success, msg = um.undo()

        assert success
        restored = mw.analysis_results_df
        assert (restored["Order_Fulfillment_Status"] == "Fulfillable").all()
        assert not um.can_undo()

    def test_undo_blocked_for_different_client(self, temp_dir):
        um, mw = make_undo_manager(temp_dir)
        mw.current_client_id = "CLIENT_B"

        # Record an operation associated with CLIENT_A
        with patch.object(um, '_save_history'):
            um.record_operation("toggle_status", "op", {}, pd.DataFrame())

        # Manually set the operation's client_id to CLIENT_A
        um.operations[0]["client_id"] = "CLIENT_A"

        with patch.object(um, '_save_history'):
            success, msg = um.undo()

        assert not success
        assert "different client" in msg

    def test_undo_blocked_for_different_session(self, temp_dir):
        session_a = temp_dir / "session_a"
        session_b = temp_dir / "session_b"
        session_a.mkdir()
        session_b.mkdir()

        um, mw = make_undo_manager(temp_dir, session_path=session_a)
        mw.session_path = session_b  # Switch to different session

        with patch.object(um, '_save_history'):
            um.record_operation("toggle_status", "op", {}, pd.DataFrame())

        # Mark the operation as belonging to session_a
        um.operations[0]["session_path"] = str(session_a)

        with patch.object(um, '_save_history'):
            success, msg = um.undo()

        assert not success
        assert "different session" in msg
