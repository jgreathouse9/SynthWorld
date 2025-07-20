import pytest
import pandas as pd
from datetime import datetime
from your_module import load_hawaii_data  # Replace with your actual module name

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
