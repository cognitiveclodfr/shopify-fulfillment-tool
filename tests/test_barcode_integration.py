"""
Integration tests for barcode generator workflow.

Tests end-to-end workflow:
- Load analysis results
- Filter by packing list
- Generate barcodes
- Generate PDF
- Save history
"""

import pytest
import pandas as pd
from pathlib import Path

from shopify_tool.barcode_processor import (
    generate_barcodes_batch,
    generate_barcodes_pdf
)
from shopify_tool.barcode_history import BarcodeHistory


@pytest.fixture
def analysis_results(tmp_path):
    """Create mock analysis results DataFrame."""
    df = pd.DataFrame([
        {
            "Order_Number": "DHL-001",
            "Shipping_Provider": "DHL",
            "Destination_Country": "DE",
            "Internal_Tag": "Priority",
            "Quantity": 2,
            "Order_Fulfillment_Status": "Fulfillable"
        },
        {
            "Order_Number": "DHL-002",
            "Shipping_Provider": "DHL",
            "Destination_Country": "FR",
            "Internal_Tag": "VIP",
            "Quantity": 1,
            "Order_Fulfillment_Status": "Fulfillable"
        },
        {
            "Order_Number": "POST-001",
            "Shipping_Provider": "PostOne",
            "Destination_Country": "BG",
            "Internal_Tag": "",
            "Quantity": 3,
            "Order_Fulfillment_Status": "Fulfillable"
        },
        {
            "Order_Number": "POST-002",
            "Shipping_Provider": "PostOne",
            "Destination_Country": "RO",
            "Internal_Tag": "Fragile",
            "Quantity": 1,
            "Order_Fulfillment_Status": "Fulfillable"
        }
    ])
    return df


@pytest.fixture
def session_dir(tmp_path):
    """Create mock session directory structure."""
    session = tmp_path / "Sessions" / "CLIENT_M" / "2026-01-16_1"
    session.mkdir(parents=True)

    # Create subdirectories
    (session / "barcodes").mkdir()
    (session / "packing_lists").mkdir()

    return session


class TestBarcodeWorkflow:
    """Integration tests for complete barcode workflow."""

    def test_full_workflow_single_courier(self, analysis_results, session_dir):
        """Test complete workflow for single courier."""
        # 1. Filter for DHL orders only
        dhl_orders = analysis_results[
            analysis_results['Shipping_Provider'] == 'DHL'
        ].copy()

        assert len(dhl_orders) == 2

        # 2. Generate sequential map for DHL orders
        sequential_map = {
            "DHL-001": 1,
            "DHL-002": 2
        }

        # 3. Generate barcodes
        output_dir = session_dir / "barcodes" / "DHL_Orders"
        output_dir.mkdir(parents=True)

        results = generate_barcodes_batch(
            df=dhl_orders,
            output_dir=output_dir,
            sequential_map=sequential_map
        )

        assert len(results) == 2
        assert all(r['success'] for r in results)

        # 4. Generate PDF
        barcode_files = [r['file_path'] for r in results]
        pdf_path = output_dir / "DHL_Orders_barcodes.pdf"

        pdf_output = generate_barcodes_pdf(
            barcode_files=barcode_files,
            output_pdf=pdf_path
        )

        assert pdf_output.exists()

        # 4. Save to history
        history_file = output_dir / "barcode_history.json"
        history_manager = BarcodeHistory(history_file)

        for result in results:
            history_manager.add_entry(result)

        # 5. Verify history
        stats = history_manager.get_statistics()
        assert stats['total_barcodes'] == 2
        assert stats['courier_breakdown'] == {"DHL": 2}

    def test_full_workflow_multiple_couriers(self, analysis_results, session_dir):
        """Test workflow with multiple packing lists."""
        couriers = analysis_results['Shipping_Provider'].unique()

        all_results = []

        # Create sequential map for all orders
        sequential_map = {
            "DHL-001": 1,
            "DHL-002": 2,
            "POST-001": 3,
            "POST-002": 4
        }

        for courier in couriers:
            # Filter orders for this courier
            courier_orders = analysis_results[
                analysis_results['Shipping_Provider'] == courier
            ].copy()

            # Generate barcodes
            output_dir = session_dir / "barcodes" / f"{courier}_Orders"
            output_dir.mkdir(parents=True, exist_ok=True)

            results = generate_barcodes_batch(
                df=courier_orders,
                output_dir=output_dir,
                sequential_map=sequential_map
            )

            all_results.extend(results)

            # Generate PDF
            barcode_files = [r['file_path'] for r in results]
            pdf_path = output_dir / f"{courier}_Orders_barcodes.pdf"

            generate_barcodes_pdf(
                barcode_files=barcode_files,
                output_pdf=pdf_path
            )

            # Save history
            history_file = output_dir / "barcode_history.json"
            history_manager = BarcodeHistory(history_file)

            for result in results:
                history_manager.add_entry(result)

        # Verify all barcodes generated
        assert len(all_results) == len(analysis_results)
        assert all(r['success'] for r in all_results)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
