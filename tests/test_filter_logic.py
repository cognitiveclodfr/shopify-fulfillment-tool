import unittest
import pandas as pd

# Import the new, testable helper functions
from shopify_tool.packing_lists import _apply_filters as apply_packing_list_filters
from shopify_tool.stock_export import _apply_filters as apply_stock_export_filters

class TestFilterLogic(unittest.TestCase):

    def setUp(self):
        """Set up a sample DataFrame for testing."""
        data = {
            'Order_Number': ['1001', '1001', '1002', '1003', '1004', '1005'],
            'Order_Fulfillment_Status': ['Fulfillable'] * 6,
            'Shipping_Provider': ['DHL', 'DHL', 'PostOne', 'DPD', 'DHL', 'PostOne'],
            'Order_Type': ['Multi', 'Multi', 'Single', 'Single', 'Multi', 'Single'],
            'Destination_Country': ['DE', 'DE', 'FR', 'DE', 'UK', 'PL'],
            'SKU': ['SKU-A', 'SKU-B', 'SKU-C', 'SKU-D', 'SKU-E', 'SKU-F'],
            'Quantity': [1, 1, 1, 1, 1, 1],
            'Product_Name': ['A', 'B', 'C', 'D', 'E', 'F']
        }
        self.df = pd.DataFrame(data)

    def test_packing_list_equals_operator(self):
        """Test the '==' operator for packing lists."""
        filters = [{'field': 'Shipping_Provider', 'operator': '==', 'value': 'DPD'}]
        filtered_df = apply_packing_list_filters(self.df, filters)
        self.assertEqual(len(filtered_df), 1)
        self.assertEqual(filtered_df['Order_Number'].iloc[0], '1003')

    def test_stock_export_not_equals_operator(self):
        """Test the '!=' operator for stock exports."""
        filters = [{'field': 'Order_Type', 'operator': '!=', 'value': 'Single'}]
        filtered_df = apply_stock_export_filters(self.df, filters)
        # Should contain only 'Multi' types (Orders 1001 and 1004)
        self.assertEqual(len(filtered_df), 3)
        self.assertTrue((filtered_df['Order_Type'] == 'Multi').all())

    def test_packing_list_in_operator(self):
        """Test the 'in' operator for packing lists."""
        filters = [{'field': 'Shipping_Provider', 'operator': 'in', 'value': ['DPD', 'PostOne']}]
        filtered_df = apply_packing_list_filters(self.df, filters)
        # Orders 1002 (PostOne), 1003 (DPD), 1005 (PostOne)
        self.assertEqual(len(filtered_df), 3)
        self.assertCountEqual(filtered_df['Order_Number'].unique().tolist(), ['1002', '1003', '1005'])

    def test_packing_list_not_in_operator(self):
        """Test the 'not in' operator."""
        filters = [{'field': 'Shipping_Provider', 'operator': 'not in', 'value': ['DPD', 'PostOne']}]
        filtered_df = apply_packing_list_filters(self.df, filters)
        # Should only contain DHL orders
        self.assertEqual(len(filtered_df), 3)
        self.assertTrue((filtered_df['Shipping_Provider'] == 'DHL').all())

    def test_packing_list_multiple_conditions(self):
        """Test multiple conditions combined with AND."""
        filters = [
            {'field': 'Shipping_Provider', 'operator': '==', 'value': 'DHL'},
            {'field': 'Order_Type', 'operator': '==', 'value': 'Multi'}
        ]
        filtered_df = apply_packing_list_filters(self.df, filters)
        # Orders 1001 and 1004 are DHL Multi
        self.assertEqual(len(filtered_df), 3)
        self.assertCountEqual(filtered_df['Order_Number'].unique().tolist(), ['1001', '1004'])

    def test_no_filters(self):
        """Test that with no filters, all fulfillable orders are returned."""
        filtered_df = apply_packing_list_filters(self.df, filters=None)
        self.assertEqual(len(filtered_df), 6) # All orders in the sample

    def test_invalid_filter_rule(self):
        """Test that an invalid or incomplete filter rule is skipped gracefully."""
        filters = [{'field': 'Shipping_Provider', 'operator': '=='}] # Missing 'value'
        filtered_df = apply_packing_list_filters(self.df, filters)
        # Should return all fulfillable orders as if no filter was applied
        self.assertEqual(len(filtered_df), 6)

if __name__ == '__main__':
    unittest.main()
