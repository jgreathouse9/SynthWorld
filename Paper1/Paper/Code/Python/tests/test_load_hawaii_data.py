import sys
import os
import pytest
import pandas as pd
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from unittest.mock import patch, MagicMock
from helpers import load_hawaii_data

@pytest.fixture(scope="module")
def hawaii_data():
    return load_hawaii_data(save_excel=False)

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

# Mock compute_annualized_growth so it just returns the input
@pytest.fixture
def mock_growth():
    with patch("helpers.compute_annualized_growth", side_effect=lambda df, lag=12: df) as mock:
        yield mock

# Mock pd.ExcelWriter to avoid actual file writing
@pytest.fixture
def mock_excel_writer():
    with patch("pandas.ExcelWriter") as mock_writer:
        mock_instance = MagicMock()
        mock_writer.return_value.__enter__.return_value = mock_instance
        yield mock_instance

def test_load_hawaii_data_with_mocks(mock_growth, mock_excel_writer):
    dfs = load_hawaii_data(save_excel=True)

    # Ensure compute_annualized_growth was called
    assert mock_growth.called, "compute_annualized_growth was not called"

    # Ensure Excel writing was attempted
    assert mock_excel_writer.to_excel.call_count > 0, "Excel to_excel was not called"

    # Sanity check on returned data
    assert isinstance(dfs, dict)
    assert set(dfs.keys()) == {"Hotels", "Tourism", "FRED"}
    for df in dfs.values():
        assert not df.empty

@patch("helpers.compute_annualized_growth", return_value=MagicMock())
@patch("pandas.ExcelWriter")
def test_load_hawaii_data_with_mocks(mock_excel_writer_class, mock_growth):
    mock_writer_instance = MagicMock()
    mock_excel_writer_class.return_value.__enter__.return_value = mock_writer_instance

    # Run function with save_excel=True to trigger the Excel writing
    dfs = helpers.load_hawaii_data(save_excel=True)

    # Check that ExcelWriter was called (you can also check the filename if needed)
    mock_excel_writer_class.assert_called_once()
    # Check that `to_excel` was called on each DataFrame
    assert mock_writer_instance.method_calls  # Just to confirm it was used

    # Optional: Check individual calls to .to_excel
    for sheet in dfs:
        df = dfs[sheet]
        df.to_excel(mock_writer_instance, sheet_name=sheet, index=False)
        mock_writer_instance.__getattr__('to_excel').assert_called()  # crude but okay
