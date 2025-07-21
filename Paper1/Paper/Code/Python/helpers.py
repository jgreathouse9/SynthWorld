import requests
import pandas as pd
import zipfile
import io

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
        growth_df[numeric_cols] = (df[numeric_cols] / df[numeric_cols].shift(lag)) - 1
        return growth_df

    # --- FRED data ---
    def load_fred():
        url = (
            "https://fred.stlouisfed.org/graph/fredgraph.csv?"
            "id=HILEIHN,HIUR,LBSSA15,HIICLAIMS"
            "&cosd=1989-01-01&coed=2020-12-31"
            "&fq=Monthly&fam=avg&transformation=pc1&line_index=1,2,3,4"
        )
        response = requests.get(url)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            with z.open('monthly.csv') as f:
                df = pd.read_csv(f)

        df.columns = [col.replace('_PC1', '') for col in df.columns]
        df = df.rename(columns={'observation_date': 'Date'})
        df['Date'] = pd.to_datetime(df['Date'])
        df = df[df['Date'] >= pd.Timestamp('1991-01-01')]
        df = df.set_index('Date')
        df = df.reindex(full_index)
        return df

    # --- UHERO data (tourism or hotels) ---
    def load_uhero_json(url: str, rename_dict: dict) -> pd.DataFrame:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        dfs = []
        for s in data["data"]["series"]:
            df = pd.DataFrame(s["values"], index=pd.to_datetime(s["dates"]), columns=[s["columns"][0]])
            dfs.append(compute_annualized_growth(df))
        df = pd.concat(dfs, axis=1)
        df.rename(columns=rename_dict, inplace=True)
        df = df.reindex(full_index)
        return df

    # Load everything
    tourism_rename = {
        "VV101sa": "Visitor Arrivals", #  (Seasonally Adjusted)
        "VV102sa": "Visitor Days" #  (Seasonally Adjusted)
    }
    hotel_rename = {
        "VH101sa": "Occupancy", # (Seasonally Adjusted)
        "VH102sa": "Mean Daily Rate", #  (Seasonally Adjusted)
        "VH103": "Revenue per Available Room"
    }
    tourism_url = "https://api.uhero.hawaii.edu/dvw/series/trend?i=VV101sa,VV102sa&m=MM102&d=DI10&f=M"
    hotel_url = "https://api.uhero.hawaii.edu/dvw/series/hotel?i=VH103,VH102sa,VH101sa&c=PVA11&f=M"

    tourism_df, hotel_df = load_uhero_json(tourism_url, tourism_rename), load_uhero_json(hotel_url, hotel_rename)
    fred_df = load_fred()

    # Combine all outcomes
    combined = pd.concat([tourism_df, hotel_df, fred_df], axis=1)

    # Final structure
    combined = combined.loc[full_index].copy()
    combined.reset_index(inplace=True)
    combined.rename(columns={'index': 'Date'}, inplace=True)
    combined['Unit'] = "Hawaii"
    combined['Mandatory Quarantine'] = (combined['Date'] >= quarantine_start).astype(int)

    # Drop rows with any NA (e.g., due to lag)
    combined.dropna(inplace=True)

    # Reorder columns
    columns = ['Date'] + [col for col in combined.columns if col not in {'Date', 'Unit', 'Mandatory Quarantine'}] + ['Unit', 'Mandatory Quarantine']
    combined = combined[columns]

    if save_excel:
        combined.to_excel(filename, index=False)

    return combined
