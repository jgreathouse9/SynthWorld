import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO


def get_msa_restaurant_series_ids():

    """
    Retrieve BLS series identifiers for full-service restaurant employment at the MSA level.

    This function downloads the BLS Current Employment Statistics (CES) dataset for the
    Leisure and Hospitality sector, filters it for MSA-level full-service restaurant
    employment series, and returns a cleaned list of series IDs suitable for fetching
    corresponding data from the FRED API.

    Returns
    -------
    list of str
        A list of cleaned and filtered BLS series IDs corresponding to
        full-service restaurant employment in U.S. metropolitan statistical areas (MSAs).

    Raises
    ------
    requests.HTTPError
        If the HTTP request to the BLS server fails.
    ValueError
        If the dataset structure has changed and expected columns are missing.

    Notes
    -----
    The returned series IDs are used to query FRED for city-level restaurant
    employment data. Only MSA-level full-service restaurant series are retained,
    excluding state- or national-level aggregates.
    """

    headers = {
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    url = 'https://download.bls.gov/pub/time.series/sm/sm.data.74.LeisureAndHospitality.Current'
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    tsv_data = StringIO(response.content.decode('utf-8'))
    df = pd.read_csv(tsv_data, sep='\t')

    # Clean whitespace
    df.columns = [col.strip() for col in df.columns]
    df['series_id'] = df['series_id'].astype(str).str.strip()

    # Filter for MSA-level full-service restaurant series
    filtered_df = df[
        (
                df['series_id'].str.contains("7072251101") |
                (df['series_id'] == "SMU11000007072251101")
        ) &
        (
                ~df['series_id'].str.contains("00000") |
                (df['series_id'] == "SMU11000007072251101")
        )
        ]

    msa_series_ids = [sid + "SA" for sid in filtered_df['series_id'].unique()]
    return msa_series_ids


def fetch_fred_series(series_id: str, cookies, headers) -> dict:
    """
    Fetch a single FRED employment time series for a specified BLS series ID.

    This function scrapes data directly from the FRED website for a given series ID,
    extracts the corresponding employment time series table, and returns it as a
    pandas DataFrame keyed by the MSA name parsed from the page title.

    Parameters
    ----------
    series_id : str
        The BLS series identifier (e.g., "SMU36505007072251101SA") corresponding
        to an MSA-level full-service restaurant employment series.
    cookies : dict
        A dictionary of session cookies used for the FRED HTTP request.
    headers : dict
        A dictionary of HTTP headers used to mimic a browser request.

    Returns
    -------
    dict of {str: pandas.DataFrame}
        A dictionary where the key is the MSA name (as parsed from the series title),
        and the value is a DataFrame with columns:
        - 'date': Observation date
        - 'value': Employment level

    Raises
    ------
    requests.HTTPError
        If the FRED data page cannot be reached.
    ValueError
        If no table is found on the page, likely due to a missing or invalid series ID.

    Notes
    -----
    The FRED interface is HTML-based and not API-driven for this dataset, so the
    function uses BeautifulSoup to parse the HTML structure. Missing or malformed
    values are skipped.
    """
    url = f'https://fred.stlouisfed.org/data/{series_id}'
    response = requests.get(url, cookies=cookies, headers=headers)

    if response.status_code == 200:
        print(f"Success: {series_id} returned 200")
    else:
        print(f"Error: {series_id} returned status code {response.status_code}")
        return {}

    soup = BeautifulSoup(response.content, 'lxml')

    # Get the title text (e.g., "Table Data - All Employees: XYZ | FRED | ...")
    raw_title = soup.find('title').text.strip()
    title = raw_title.split('|')[0].replace('Table Data - ', '').replace(
        "All Employees: Leisure and Hospitality: Full-Service Restaurants in ", "").strip()

    # Parse table
    table = soup.find('table', {'id': 'data-table-observations'})
    if not table:
        raise ValueError(f"No table found for series ID {series_id}")

    rows = table.find('tbody').find_all('tr')
    data = []
    for row in rows:
        date = row.find('th').text.strip()
        value = row.find('td').text.strip()
        try:
            data.append((date, float(value)))
        except ValueError:
            continue  # skip missing/invalid data

    df = pd.DataFrame(data, columns=['date', 'value'])
    df['date'] = pd.to_datetime(df['date'])

    return {title: df}


def fetch_multiple_series(series_id_list, cookies, headers):
    """
    Fetch and compile restaurant employment time series across multiple MSAs.

    For each BLS series ID in the provided list, this function retrieves employment data
    using `fetch_fred_series`, harmonizes column names, appends MSA identifiers, and
    combines all results into a single DataFrame. It also computes year-over-year
    employment growth rates and filters the dataset for the relevant analysis period.

    Parameters
    ----------
    series_id_list : list of str
        List of BLS series identifiers corresponding to MSA-level restaurant employment.
    cookies : dict
        Session cookies passed to each FRED request.
    headers : dict
        HTTP request headers for accessing FRED.

    Returns
    -------
    pandas.DataFrame
        A cleaned and consolidated DataFrame containing:
        - 'MSA': Metropolitan statistical area name
        - 'Time': Observation date
        - 'Employment': Employment level (scaled by 1,000)
        - 'yoy_growth': Year-over-year employment growth rate
        - 'Key to NYC': Indicator for whether the Key to NYC vaccine mandate was active

    Raises
    ------
    ValueError
        If a required series fails to download or cannot be parsed.
    Exception
        Any unhandled errors during HTTP requests or parsing are logged and skipped.

    Notes
    -----
    - Employment figures are multiplied by 1,000 to match BLS scaling conventions.
    - Growth rates are computed as 12-month percentage changes within each MSA.
    - Observations after August 2022 and any entries containing "Jersey City" are dropped.
    - A binary column 'Key to NYC' marks the post-mandate period for New York City
      beginning in August 2021.
    """
    all_data = []
    for series_id in series_id_list:
        try:
            series_dict = fetch_fred_series(series_id, cookies, headers)
            for title, df in series_dict.items():
                df = df.rename(columns={"date": "Time", "value": "Employment"})
                df["MSA"] = title
                all_data.append(df)
        except Exception as e:
            print(f"Failed to fetch {series_id}: {e}")
            continue
    combined_df = pd.concat(all_data, ignore_index=True)

    # Multiply employment by 1000 (per your original code)
    combined_df['Employment'] = combined_df['Employment'] * 1000

    # Compute YoY growth by MSA
    final_df = combined_df.sort_values(['MSA', 'Time'])
    final_df['yoy_growth'] = final_df.groupby('MSA')['Employment'].pct_change(periods=12)

    # Drop rows with missing YoY growth
    final_df = final_df.dropna(subset=['yoy_growth'])

    # Define August 2022 as the cutoff
    cutoff = pd.to_datetime('2022-08-01')

    # Drop unwanted rows
    final_df = final_df[~final_df['MSA'].str.contains("Jersey City", na=False)]
    final_df = final_df[final_df['Time'] <= cutoff]

    start_ktc = pd.to_datetime('2021-08-01')

    # Your city-level enforcement dates (MSA names as keys)
    city_dates = {
        "New York City": "2021-08-01",
        "San Francisco": "2021-08-20",
        "New Orleans": "2021-08-16",
        "Los Angeles": "2021-11-04"
    }

    # Initialize Mandate column to 0
    final_df['Mandate'] = 0

    final_df.rename(columns={"Time": "Date"}, inplace=True)

    # Loop through each MSA and enforcement date
    for msa, date in city_dates.items():
        mandate_date = pd.to_datetime(date)
        final_df.loc[(final_df['MSA'].str.contains(msa, case=False, na=False)) & (final_df['Date'] >= mandate_date), 'Mandate'] = 1



    return final_df
