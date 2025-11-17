"""
Unit tests for refactored phase functions in core.py

Simplified tests that verify core phase functions work correctly.
Tests focus on the most important functionality without complex mocking.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock
from shopify_tool import core


class TestValidateAndPrepareInputs:
    """Tests for _validate_and_prepare_inputs phase function."""

    def test_validate_session_mode_with_session_path(self, tmp_path):
        """Test validation when session_path is provided."""
        session_path = tmp_path / "session"
        session_path.mkdir()

        # Mock session manager
        session_manager = Mock()
        session_manager.get_session_path.return_value = str(session_path)

        use_session, working_path, error, path = core._validate_and_prepare_inputs(
            stock_file_path=None,
            orders_file_path=None,
            output_dir_path=str(tmp_path),
            client_id="TEST",
            session_manager=session_manager,
            session_path=str(session_path)
        )

        assert use_session is True
        assert error is None
        assert path == str(session_path)

    def test_validate_legacy_mode_without_session(self, tmp_path):
        """Test validation in legacy mode (no session)."""
        stock_file = tmp_path / "stock.csv"
        stock_file.write_text("SKU,Stock\nA,10")

        orders_file = tmp_path / "orders.csv"
        orders_file.write_text("Order,SKU\n1,A")

        use_session, working_path, error, path = core._validate_and_prepare_inputs(
            stock_file_path=str(stock_file),
            orders_file_path=str(orders_file),
            output_dir_path=str(tmp_path),
            client_id=None,
            session_manager=None,
            session_path=None
        )

        assert use_session is False
        assert error is None

    def test_validate_missing_files_in_legacy_mode(self, tmp_path):
        """Test validation passes (file validation happens in load phase)."""
        use_session, working_path, error, path = core._validate_and_prepare_inputs(
            stock_file_path="/nonexistent/stock.csv",
            orders_file_path="/nonexistent/orders.csv",
            output_dir_path=str(tmp_path),
            client_id=None,
            session_manager=None,
            session_path=None
        )

        assert use_session is False
        # _validate_and_prepare_inputs doesn't check if files exist
        # That's done in _load_and_validate_files
        assert error is None


class TestLoadAndValidateFiles:
    """Tests for _load_and_validate_files phase function."""

    def test_load_missing_file_raises_error(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            core._load_and_validate_files(
                stock_file_path="/nonexistent/stock.csv",
                orders_file_path="/nonexistent/orders.csv",
                stock_delimiter=",",
                orders_delimiter=",",
                config={}
            )


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
