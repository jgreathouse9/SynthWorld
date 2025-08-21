import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO

def get_msa_restaurant_series_ids():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Referer': 'https://www.bls.gov/',
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
    return final_df
