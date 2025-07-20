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
        "Revenue per Available Room": [140, 157.5],
        "Mandatory Quarantine": [0, 0],
        "Unit": ["Hawaii", "Hawaii"]
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

@patch("helpers.requests.get")
@patch("helpers.compute_annualized_growth")
@patch("pandas.ExcelWriter")
def test_load_hawaii_data_with_mocks(mock_excel_writer_class, mock_growth, mock_requests_get, dummy_growth_df):
    # --- Mock DBEDT and FRED responses ---
    def mock_response_json(varname, values):
        return {
            "data": {
                "series": [{
                    "columns": [varname],
                    "dates": ["2020-01-01", "2020-02-01"],
                    "values": values
                }]
            }
        }

    def requests_side_effect(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None

        if "hotel" in url:
            mock_resp.json.return_value = {
                "data": {
                    "series": [
                        {"columns": ["VH101sa"], "dates": ["2020-01-01", "2020-02-01"], "values": [70, 75]},
                        {"columns": ["VH102sa"], "dates": ["2020-01-01", "2020-02-01"], "values": [200, 210]},
                        {"columns": ["VH103"], "dates": ["2020-01-01", "2020-02-01"], "values": [140, 157.5]}
                    ]
                }
            }
        elif "trend" in url:
            mock_resp.json.return_value = {
                "data": {
                    "series": [{
                        "columns": ["VISITORDAYS"],
                        "dates": ["2020-01-01", "2020-02-01"],
                        "values": [1_000_000, 1_100_000]
                    }]
                }
            }
        elif "HIICLAIMS" in url:
            mock_resp.content = (
                b"observation_date,HIICLAIMS\n"
                b"2020-01-01,3000\n"
                b"2020-02-01,3200\n"
            )
        elif "HILEIHN" in url:
            mock_resp.content = (
                b"observation_date,HILEIHN\n"
                b"2020-01-01,600000\n"
                b"2020-02-01,610000\n"
            )
        else:
            raise ValueError(f"Unexpected URL: {url}")

        return mock_resp

    mock_requests_get.side_effect = requests_side_effect

    # --- Mock compute_annualized_growth ---
    mock_growth.return_value = dummy_growth_df

    # --- Mock ExcelWriter context ---
    mock_writer_instance = MagicMock()
    mock_excel_writer_class.return_value.__enter__.return_value = mock_writer_instance

    # --- Run function ---
    dfs = load_hawaii_data(save_excel=True)

    # --- Validate ---
    assert isinstance(dfs, dict)
    assert set(dfs.keys()) == {"Hotels", "Tourism", "FRED"}
    for name, df in dfs.items():
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    assert mock_growth.called
    assert mock_excel_writer_class.called
    assert mock_writer_instance.method_calls
