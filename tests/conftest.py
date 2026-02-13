"""Shared pytest fixtures for the test suite."""

import os
import tempfile
import shutil
from pathlib import Path

import pandas as pd
import pytest

# Use offscreen platform for headless CI/CD
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture(scope="session")
def qapp():
    """Reusable QApplication instance (created once per test session)."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_dir():
    """Temporary directory that is automatically cleaned up after each test."""
    path = tempfile.mkdtemp()
    yield Path(path)
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def sample_dataframe():
    """Standard analysis-results-style DataFrame for table/model tests."""
    return pd.DataFrame({
        "Order_Number": ["ORD-001", "ORD-001", "ORD-002", "ORD-003"],
        "SKU": ["SKU-A", "SKU-B", "SKU-C", "SKU-D"],
        "Quantity": [1, 2, 3, 1],
        "Order_Fulfillment_Status": [
            "Fulfillable", "Fulfillable", "Not Fulfillable", "Fulfillable"
        ],
        "System_note": [None, None, "Cannot fulfill: out of stock", "Repeat order"],
    })


@pytest.fixture
def minimal_dataframe():
    """Minimal DataFrame with no special columns (baseline for model tests)."""
    return pd.DataFrame({
        "col_a": ["x", "y", "z"],
        "col_b": [1, 2, 3],
    })
