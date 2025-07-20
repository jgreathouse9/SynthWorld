import sys
import os
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helpers import load_hawaii_data

@pytest.fixture(scope="module")
def hawaii_data():
    return load_hawaii_data(save_excel=False)

@pytest.fixture
def dummy_growth_df():
    df = pd.DataFrame({
        "Occupancy (Seasonally Adjusted)": [70, 75],
        "Mean Daily Rate (Seasonally Adjusted)": [200, 210],
        "Revenue per Available Room": [140, 157.5],
        "Unit": ["Hawaii", "Hawaii"],
        "Mandatory Quarantine": [0, 0],
    }, index=pd.to_datetime(["2020-01-01", "2020-02-01"]))
    return df

@patch("helpers.requests.get")
@patch("helpers.compute_annualized_growth")
@patch("pandas.ExcelWriter")
def test_load_hawaii_data_with_mocks(mock_excel_writer_class, mock_growth, mock_requests_get, dummy_growth_df):
    # Mock requests.get side effect to return fake data with dates
    def requests_side_effect(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None

        if "hotel" in url:
            mock_resp.json.return_value = {
                "data": {
                    "series": [
                        {"columns": ["VH101sa"], "dates": ["2020-01-01", "2020-02-01"], "values": [70, 75]},
                        {"columns": ["VH102sa"], "dates": ["2020-01-01", "2020-02-01"], "values": [200, 210]},
                        {"columns": ["VH103"], "dates": ["2020-01-01", "2020-02-01"], "values": [140, 157.5]},
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

    # Mock compute_annualized_growth returns the dummy dataframe with datetime index
    mock_growth.return_value = dummy_growth_df

    # Mock ExcelWriter context manager
    mock_writer_instance = MagicMock()
    mock_excel_writer_class.return_value.__enter__.return_value = mock_writer_instance

    # Run the actual function (with save_excel=True to test Excel writing logic)
    dfs = load_hawaii_data(save_excel=True)

    # Basic assertions
    assert isinstance(dfs, dict)
    assert set(dfs.keys()) == {"Hotels", "Tourism", "FRED"}

    # Check that compute_annualized_growth was called once
    assert mock_growth.called

    # Check that ExcelWriter was used
    mock_excel_writer_class.assert_called_once()

    # Check that some to_excel calls were made on the mock ExcelWriter instance
    assert any("to_excel" in call[0] for call in mock_writer_instance.method_calls)

    # Check index types in returned DataFrames (they should be datetime)
    for df in dfs.values():
        assert pd.api.types.is_datetime64_any_dtype(df.index), "Index is not datetime"

    # Check Mandatory Quarantine column values are 0 or 1
    for df in dfs.values():
        assert set(df["Mandatory Quarantine"].unique()).issubset({0, 1})
