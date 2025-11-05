"""
Tests for centralized logging configuration with JSON formatting.

This module tests the logger_config module including:
- JSON formatting with structured fields
- Centralized server logging
- Date-based log files
- RotatingFileHandler configuration
- Context-aware logging
"""

import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from shopify_tool.logger_config import (
    JSONFormatter,
    log_with_context,
    setup_logging,
)


class TestJSONFormatter:
    """Tests for the JSONFormatter class."""

    def test_basic_formatting(self):
        """Test basic JSON log formatting."""
        formatter = JSONFormatter(tool_name="test_tool")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        record.module = "test_module"

        output = formatter.format(record)
        log_data = json.loads(output)

        assert log_data["level"] == "INFO"
        assert log_data["tool"] == "test_tool"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert "timestamp" in log_data

    def test_formatting_with_context(self):
        """Test JSON formatting with client_id and session_id."""
        formatter = JSONFormatter(tool_name="shopify_tool")
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=100,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        record.funcName = "process_order"
        record.module = "core"
        record.client_id = "CLIENT_M"
        record.session_id = "2025-11-05_1"

        output = formatter.format(record)
        log_data = json.loads(output)

        assert log_data["level"] == "WARNING"
        assert log_data["client_id"] == "CLIENT_M"
        assert log_data["session_id"] == "2025-11-05_1"
        assert log_data["message"] == "Warning message"

    def test_formatting_without_context(self):
        """Test JSON formatting when context fields are not provided."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=200,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        record.funcName = "error_function"
        record.module = "error_module"

        output = formatter.format(record)
        log_data = json.loads(output)

        assert log_data["client_id"] is None
        assert log_data["session_id"] is None
        assert log_data["level"] == "ERROR"

    def test_formatting_with_exception(self):
        """Test JSON formatting with exception information."""
        formatter = JSONFormatter()
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=300,
            msg="Error with exception",
            args=(),
            exc_info=exc_info,
        )
        record.funcName = "exception_function"
        record.module = "exception_module"

        output = formatter.format(record)
        log_data = json.loads(output)

        assert "exception" in log_data
        assert "ValueError" in log_data["exception"]
        assert "Test exception" in log_data["exception"]

    def test_timestamp_format(self):
        """Test that timestamp is in ISO format."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=400,
            msg="Timestamp test",
            args=(),
            exc_info=None,
        )
        record.funcName = "timestamp_function"
        record.module = "timestamp_module"

        output = formatter.format(record)
        log_data = json.loads(output)

        # Verify timestamp is in ISO format
        timestamp = datetime.fromisoformat(log_data["timestamp"])
        assert isinstance(timestamp, datetime)


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def test_local_logging_setup(self):
        """Test logging setup with local directory (no server path)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("shopify_tool.logger_config.Path") as mock_path:
                # Mock Path to use temp directory
                mock_path.return_value = Path(temp_dir) / "logs"

                logger = setup_logging()

                assert logger.name == "ShopifyToolLogger"
                assert logger.level == logging.INFO
                assert len(logger.handlers) == 2  # File handler + Stream handler

    def test_server_logging_setup(self):
        """Test logging setup with centralized server path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server_path = temp_dir
            logger = setup_logging(server_base_path=server_path)

            assert logger.name == "ShopifyToolLogger"
            # Check that log directory was created
            log_dir = Path(server_path) / "Logs" / "shopify_tool"
            assert log_dir.exists()

    def test_date_based_log_filename(self):
        """Test that log files use date-based naming."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(server_base_path=temp_dir)

            # Find the created log file
            log_dir = Path(temp_dir) / "Logs" / "shopify_tool"
            log_files = list(log_dir.glob("*.log"))

            assert len(log_files) == 1
            # Check filename matches YYYY-MM-DD format
            expected_filename = f"{datetime.now().strftime('%Y-%m-%d')}.log"
            assert log_files[0].name == expected_filename

    def test_rotating_file_handler_config(self):
        """Test that RotatingFileHandler is configured correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(server_base_path=temp_dir)

            # Find the file handler
            file_handler = None
            for handler in logger.handlers:
                if hasattr(handler, "maxBytes"):
                    file_handler = handler
                    break

            assert file_handler is not None
            assert file_handler.maxBytes == 10 * 1024 * 1024  # 10MB
            assert file_handler.backupCount == 30

    def test_logger_context_storage(self):
        """Test that client_id and session_id are stored in logger."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(
                server_base_path=temp_dir, client_id="CLIENT_A", session_id="2025-11-05_2"
            )

            assert hasattr(logger, "client_id")
            assert hasattr(logger, "session_id")
            assert logger.client_id == "CLIENT_A"
            assert logger.session_id == "2025-11-05_2"

    def test_multiple_setup_calls(self):
        """Test that calling setup_logging multiple times doesn't duplicate handlers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger1 = setup_logging(server_base_path=temp_dir)
            handler_count_1 = len(logger1.handlers)

            logger2 = setup_logging(server_base_path=temp_dir)
            handler_count_2 = len(logger2.handlers)

            assert handler_count_1 == handler_count_2
            assert logger1 is logger2  # Same logger instance

    def test_log_directory_creation(self):
        """Test that log directories are created if they don't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            server_path = Path(temp_dir) / "new_server_path"
            assert not server_path.exists()

            setup_logging(server_base_path=str(server_path))

            log_dir = server_path / "Logs" / "shopify_tool"
            assert log_dir.exists()


class TestLogWithContext:
    """Tests for the log_with_context helper function."""

    def test_log_with_explicit_context(self):
        """Test logging with explicitly provided context."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(server_base_path=temp_dir)
            log_with_context(
                logger,
                logging.INFO,
                "Test message with context",
                client_id="CLIENT_B",
                session_id="2025-11-05_3",
            )

            # Read the log file
            log_dir = Path(temp_dir) / "Logs" / "shopify_tool"
            log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

            with open(log_file, "r", encoding="utf-8") as f:
                log_line = f.readline()
                log_data = json.loads(log_line)

            assert log_data["client_id"] == "CLIENT_B"
            assert log_data["session_id"] == "2025-11-05_3"
            assert log_data["message"] == "Test message with context"

    def test_log_with_logger_context(self):
        """Test logging using context stored in logger."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(
                server_base_path=temp_dir, client_id="CLIENT_C", session_id="2025-11-05_4"
            )
            log_with_context(logger, logging.WARNING, "Test message using logger context")

            # Read the log file
            log_dir = Path(temp_dir) / "Logs" / "shopify_tool"
            log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

            with open(log_file, "r", encoding="utf-8") as f:
                log_line = f.readline()
                log_data = json.loads(log_line)

            assert log_data["client_id"] == "CLIENT_C"
            assert log_data["session_id"] == "2025-11-05_4"
            assert log_data["level"] == "WARNING"

    def test_log_without_context(self):
        """Test logging without any context."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(server_base_path=temp_dir)

            # Clear any context from previous tests
            if hasattr(logger, "client_id"):
                delattr(logger, "client_id")
            if hasattr(logger, "session_id"):
                delattr(logger, "session_id")

            log_with_context(logger, logging.ERROR, "Test message without context")

            # Read the log file
            log_dir = Path(temp_dir) / "Logs" / "shopify_tool"
            log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

            with open(log_file, "r", encoding="utf-8") as f:
                log_line = f.readline()
                log_data = json.loads(log_line)

            assert log_data["client_id"] is None
            assert log_data["session_id"] is None
            assert log_data["level"] == "ERROR"


class TestLogFileIntegration:
    """Integration tests for actual log file creation and writing."""

    def test_actual_log_file_creation(self):
        """Test that log files are actually created on disk."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(server_base_path=temp_dir)
            logger.info("Test log entry")

            log_dir = Path(temp_dir) / "Logs" / "shopify_tool"
            log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

            assert log_file.exists()
            assert log_file.stat().st_size > 0

    def test_multiple_log_entries(self):
        """Test writing multiple log entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(
                server_base_path=temp_dir, client_id="CLIENT_D", session_id="2025-11-05_5"
            )

            # Write multiple log entries
            for i in range(5):
                log_with_context(logger, logging.INFO, f"Log entry {i}")

            # Read and verify all entries
            log_dir = Path(temp_dir) / "Logs" / "shopify_tool"
            log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            assert len(lines) == 5
            for i, line in enumerate(lines):
                log_data = json.loads(line)
                assert log_data["message"] == f"Log entry {i}"
                assert log_data["client_id"] == "CLIENT_D"

    def test_json_parsability(self):
        """Test that all log entries are valid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(server_base_path=temp_dir)

            # Write various log levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            log_dir = Path(temp_dir) / "Logs" / "shopify_tool"
            log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    # This will raise an exception if JSON is invalid
                    log_data = json.loads(line)
                    assert "timestamp" in log_data
                    assert "level" in log_data
                    assert "message" in log_data

    def test_console_output_format(self):
        """Test that console output uses simple format, not JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            import io
            from contextlib import redirect_stderr

            # Capture stderr
            stderr_capture = io.StringIO()

            with redirect_stderr(stderr_capture):
                logger = setup_logging(server_base_path=temp_dir)
                logger.info("Console test message")

            console_output = stderr_capture.getvalue()

            # Console output should NOT be JSON
            assert "Console test message" in console_output
            assert "INFO:" in console_output
            # Should not look like JSON
            assert not console_output.strip().startswith("{")


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_unicode_in_log_messages(self):
        """Test logging with Unicode characters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(server_base_path=temp_dir)
            logger.info("Тестове повідомлення з Unicode символами")

            log_dir = Path(temp_dir) / "Logs" / "shopify_tool"
            log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

            with open(log_file, "r", encoding="utf-8") as f:
                log_line = f.readline()
                log_data = json.loads(log_line)

            assert log_data["message"] == "Тестове повідомлення з Unicode символами"

    def test_special_characters_in_context(self):
        """Test logging with special characters in context fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(server_base_path=temp_dir)
            log_with_context(
                logger,
                logging.INFO,
                "Test message",
                client_id='CLIENT_"SPECIAL"',
                session_id="2025-11-05_<test>",
            )

            log_dir = Path(temp_dir) / "Logs" / "shopify_tool"
            log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

            with open(log_file, "r", encoding="utf-8") as f:
                log_line = f.readline()
                log_data = json.loads(log_line)

            assert log_data["client_id"] == 'CLIENT_"SPECIAL"'
            assert log_data["session_id"] == "2025-11-05_<test>"

    def test_very_long_message(self):
        """Test logging with very long message."""
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = setup_logging(server_base_path=temp_dir)
            long_message = "A" * 10000
            logger.info(long_message)

            log_dir = Path(temp_dir) / "Logs" / "shopify_tool"
            log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

            with open(log_file, "r", encoding="utf-8") as f:
                log_line = f.readline()
                log_data = json.loads(log_line)

            assert log_data["message"] == long_message
