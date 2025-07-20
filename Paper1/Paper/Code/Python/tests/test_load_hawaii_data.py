import sys
import os
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers import load_hawaii_data

# -----------------------
# Fixtures and Mocks
# -----------------------

@pytest.fixture(scope="module")
def hawaii_data():
    return load_hawaii_data(save_excel=False)

@pytest.fixture
def dummy_growth_df():
    return pd.DataFrame({
        "Occupancy (Seasonally Adjusted)": [70, 75],
        "Mean Daily Rate (Seasonally Adjusted)": [200, 210],
        "Revenue per Available Room": [140, 157.5]
    }, index=pd.to_datetime(["2020-01-01", "2020-02-01"]))

# -----------------------
# Tests on Real Data (no mocks)
# -----------------------

def test_keys_present(hawaii_data):
    assert "Hotels" in hawaii_data
    assert "Tourism" in hawaii_data
    assert "FRED" in hawaii_data

@pytest.mark.parametrize("dataset,expected_cols", [
    ("Hotels", [
        "Date", "Occupancy (Seasonally Adjusted)", "Mean Daily Rate (Seasonally Adjusted)",
        "Revenue per Available Room", "Unit", "Mandatory Quarantine"
    ]),
    ("Tourism", [
        "Date", "Visitor Arrivals (Seasonally Adjusted)", "Visitor Days (Seasonally Adjusted)",
        "Unit", "Mandatory Quarantine"
    ]),
    ("FRED", [
        "Date", "Leisure and Hospitality Employment YoY", "Initial Unemployment Claims YoY",
        "Unit", "Mandatory Quarantine"
    ])
])
def test_expected_columns(dataset, expected_cols, hawaii_data):
    df = hawaii_data[dataset]
    for col in expected_cols:
        assert col in df.columns, f"{col} missing from {dataset}"

def test_date_is_datetime(hawaii_data):
    for df in hawaii_data.values():
        assert pd.api.types.is_datetime64_any_dtype(df["Date"])

def test_data_cutoff(hawaii_data):
    for name, df in hawaii_data.items():
        assert df["Date"].max() < datetime(2021, 1, 1), f"{name} data goes past 2020"

def test_no_missing_values(hawaii_data):
    for name, df in hawaii_data.items():
        assert not df.isnull().any().any(), f"Missing values in {name}"

def test_numeric_columns_are_numeric(hawaii_data):
    numeric_cols = {
        "Hotels": ["Occupancy (Seasonally Adjusted)", "Mean Daily Rate (Seasonally Adjusted)", "Revenue per Available Room"],
        "Tourism": ["Visitor Arrivals (Seasonally Adjusted)", "Visitor Days (Seasonally Adjusted)"],
        "FRED": ["Leisure and Hospitality Employment YoY", "Initial Unemployment Claims YoY"]
    }
    for dataset, cols in numeric_cols.items():
        df = hawaii_data[dataset]
        for col in cols:
            assert pd.api.types.is_numeric_dtype(df[col]), f"{col} in {dataset} is not numeric"

def test_quarantine_flag_is_binary(hawaii_data):
    for name, df in hawaii_data.items():
        assert set(df["Mandatory Quarantine"].unique()).issubset({0, 1}), f"Non-binary quarantine flag in {name}"

# -----------------------
# Mocked Tests
# -----------------------

@patch("helpers.compute_annualized_growth")
@patch("pandas.ExcelWriter")
def test_load_hawaii_data_with_mocks(mock_excel_writer_class, mock_growth, dummy_growth_df):
    # Use dummy DataFrame instead of MagicMock to avoid comparison errors
    mock_growth.return_value = dummy_growth_df

    # Setup mock ExcelWriter context manager
    mock_writer_instance = MagicMock()
    mock_excel_writer_class.return_value.__enter__.return_value = mock_writer_instance

    # Run the function
    dfs = load_hawaii_data(save_excel=True)

    # Validate function behavior
    assert isinstance(dfs, dict)
    assert set(dfs.keys()) == {"Hotels", "Tourism", "FRED"}

    # Ensure compute_annualized_growth was called
    assert mock_growth.called

    # Ensure ExcelWriter and to_excel were called
    mock_excel_writer_class.assert_called_once()
    assert mock_writer_instance.method_calls  # basic smoke check
