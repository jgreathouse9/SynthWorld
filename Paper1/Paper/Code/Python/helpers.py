import requests
import pandas as pd

def load_hawaii_data(compute_growth=True, save_excel=False, filename="hawaii_data.xlsx") -> pd.DataFrame:
    """
    Returns a wide-format DataFrame with 360 rows (one per month from 1991-01 to 2020-12)
    and 9 outcome variables (2 tourism + 3 hotel + 4 FRED), plus Unit, Date, and Mandatory Quarantine.

    Parameters
    ----------
    compute_growth : bool
        Whether to compute 12-month annualized growth rates for UHERO data.
    save_excel : bool
        Whether to save the resulting dataset to Excel.
    filename : str
        Path to Excel file (if saving).

    Returns
    -------
    pd.DataFrame
        A DataFrame with shape (360, 12) containing outcomes and metadata.
    """
    quarantine_start = pd.Timestamp("2020-03-01")
    start_date = pd.Timestamp("1991-01-01")
    end_date = pd.Timestamp("2020-12-01")
    full_index = pd.date_range(start=start_date, end=end_date, freq='MS')

    def compute_annualized_growth(df, lag=12):
        numeric_cols = df.select_dtypes(include='number').columns
        growth_df = df.copy()
        growth_df[numeric_cols] = ((df[numeric_cols] / df[numeric_cols].shift(lag)) - 1)*100
        return growth_df

    # --- FRED data (simplified) ---
    def load_fred():
        fred_url = (
            "https://fred.stlouisfed.org/graph/fredgraph.csv?"
            "id=HILEIHN,HIUR,LBSSA15,SMU15000007072100001SA,HIPHCI"
            "&cosd=1990-01-01&coed=2020-12-31"
            "&fq=Monthly&fam=avg&transformation=pc1&line_index=1,2,3,4,5"
        )
        df = pd.read_csv(fred_url)
        df = df.rename(columns={"observation_date": "Date"})
        df["Date"] = pd.to_datetime(df["Date"])
        df = df[df["Date"] >= start_date]
        df = df.rename(columns={
            "observation_date": "Date",
            "HILEIHN_PC1": "Total Leisure Emp",
            "HIUR_PC1": "Unemp Rate",
            "LBSSA15_PC1": "LFP",
            "SMU15000007072100001SA_PC1": "Accommodation Emp",
            "HIPHCI_PC1": "Econ Activity Index"
        })
        df = df.set_index("Date")
        df = df.reindex(full_index)
        return df

    # --- UHERO tourism or hotel data ---
    def load_uhero_json(url: str, rename_dict: dict) -> pd.DataFrame:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        dfs = []
        for s in data["data"]["series"]:
            df = pd.DataFrame(s["values"], index=pd.to_datetime(s["dates"]), columns=[s["columns"][0]])
            if compute_growth:
                df = compute_annualized_growth(df)
            dfs.append(df)
        df = pd.concat(dfs, axis=1)
        df.rename(columns=rename_dict, inplace=True)
        df = df.reindex(full_index)
        return df

    tourism_rename = {
        "VV101sa": "Visitor Arrivals",
        "VV102sa": "Visitor Days"
    }
    hotel_rename = {
        "VH101sa": "Occupancy",
        "VH102sa": "Mean Daily Rate",
        "VH103": "Revenue per Available Room"
    }

    tourism_url = "https://api.uhero.hawaii.edu/dvw/series/trend?i=VV101sa,VV102sa&m=MM102&d=DI10&f=M"
    hotel_url = "https://api.uhero.hawaii.edu/dvw/series/hotel?i=VH103,VH102sa,VH101sa&c=PVA11&f=M"

    tourism_df = load_uhero_json(tourism_url, tourism_rename)
    hotel_df = load_uhero_json(hotel_url, hotel_rename)
    fred_df = load_fred()

    combined = pd.concat([tourism_df, hotel_df, fred_df], axis=1)
    combined = combined.loc[full_index].copy()
    combined.reset_index(inplace=True)
    combined.rename(columns={"index": "Date"}, inplace=True)

    combined["Unit"] = "Hawaii"
    combined["Mandatory Quarantine"] = (combined["Date"] >= quarantine_start).astype(int)
    combined.dropna(inplace=True)

    # Column order
    nonmeta = [c for c in combined.columns if c not in {"Date", "Unit", "Mandatory Quarantine"}]
    combined = combined[["Date"] + nonmeta + ["Unit", "Mandatory Quarantine"]]

    if save_excel:
        combined.to_excel(filename, index=False)
        print(f"Saved cleaned data to {filename}")

    return combined



def get_taxdata( save_excel=False, filename="HawaiiTaxData.xlsx"):
    # Common headers
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": "Bearer -VI_yuv0UzZNy4av1SM5vQlkfPK_JKnpGfMzuJR7d0M=",
        "Origin": "https://data.uhero.hawaii.edu",
        "Referer": "https://data.uhero.hawaii.edu/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    base_url = "https://api.uhero.hawaii.edu/v1/measurement/series"

    def extract_state_monthly_dataframe(data, dataset_name):
        try:
            for i, series in enumerate(data['data']):
                if (series.get('geography', {}).get('handle') == 'HI' and
                        series.get('frequencyShort') == 'M'):
                    values = series['seriesObservations']['transformationResults'][0]['values']
                    dates = series['seriesObservations']['transformationResults'][0]['dates']
                    df = pd.DataFrame({
                        'Date': pd.to_datetime(dates),
                        dataset_name: [float(v) * 1000 for v in values]  # Multiply by 1000 here
                    })
                    df = df[(df['Date'] >= '1990-01-01') & (df['Date'] < '2021-01-01')].reset_index(drop=True)
                    return df
            return None
        except Exception as e:
            print(f"{dataset_name}: Error extracting series – {str(e)}")
            return None

    # Request for GET (id=163887)
    response_get = requests.get(base_url, params={"id": 163887, "expand": "true"}, headers=headers)
    get_df = extract_state_monthly_dataframe(response_get.json(), "GET Taxes") if response_get.ok else None

    # Request for TAT (id=163872)
    response_tat = requests.get(base_url, params={"id": 163872, "expand": "true"}, headers=headers)
    tat_df = extract_state_monthly_dataframe(response_tat.json(), "TAT Taxes") if response_tat.ok else None

    if get_df is not None and tat_df is not None:
        df = pd.merge(get_df, tat_df, on="Date", how="inner")

        # Compute 12-month percent change
        df["GET YoY"] = df["GET Taxes"].pct_change(periods=12) * 100
        df["TAT YoY"] = df["TAT Taxes"].pct_change(periods=12) * 100

        # Drop rows with missing values
        df = df.dropna().reset_index(drop=True)
        # Add "Mandatory Quarantine" column
        df["Mandatory Quarantine"] = df["Date"] >= pd.to_datetime("2020-03-01")

        # Add "Unit" column
        df["Unit"] = "Hawaii"
        if save_excel:
            combined.to_excel(filename, index=False)
            print(f"Saved cleaned data to {filename}")
        return df
    else:
        print("Failed to retrieve one or both datasets.")
        return None


