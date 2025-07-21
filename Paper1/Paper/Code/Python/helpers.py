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
        growth_df[numeric_cols] = (df[numeric_cols] / df[numeric_cols].shift(lag)) - 1
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
            "HILEIHN_PC1": "Total Leisure eMP",
            "HIUR_PC1": "Unemp Rate",
            "LBSSA15_PC1": "LFP",
            "SMU15000007072100001SA_PC1": "Accomodation Emp",
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
