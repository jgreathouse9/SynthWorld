import requests
import pandas as pd
import matplotlib.pyplot as plt

def compute_annualized_growth(df, lag=12):
    numeric_cols = df.select_dtypes(include='number').columns
    growth_df = df.copy()
    growth_df[numeric_cols] = (df[numeric_cols] / df[numeric_cols].shift(lag)) - 1
    return growth_df

def load_hawaii_data(save_excel=True, filename="hawaii_data.xlsx", compute_growth=True):
    quarantine_start = pd.Timestamp("2020-03-01")
    cutoff_date = pd.Timestamp("2021-01-01")

    urls = {
        "Hotels": "https://api.uhero.hawaii.edu/dvw/series/hotel?i=VH103,VH102sa,VH101sa&c=PVA11&f=M",
        "Tourism": "https://api.uhero.hawaii.edu/dvw/series/trend?i=VV101sa,VV102sa&m=MM102&d=DI10&f=M",
        "FRED_LHE": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=HILEIHN&cosd=1990-01-01&coed=2020-12-31&fq=Monthly&fam=avg&transformation=pc1",
        "FRED_UI":  "https://fred.stlouisfed.org/graph/fredgraph.csv?id=HIICLAIMS&cosd=1990-01-01&coed=2020-12-31&fq=Monthly&fam=avg&transformation=pc1"
    }

    dfs = {}

    # --- Load Hotels data ---
    response_hotel = requests.get(urls["Hotels"])
    response_hotel.raise_for_status()
    data_hotel = response_hotel.json()
    dfs_hotel = []
    for s in data_hotel["data"]["series"]:
        df = pd.DataFrame(s["values"], index=pd.to_datetime(s["dates"]), columns=[s["columns"][0]])
        dfs_hotel.append(df)
    df_hotels = pd.concat(dfs_hotel, axis=1)

    # Ensure datetime index after concat
    if not pd.api.types.is_datetime64_any_dtype(df_hotels.index):
        df_hotels.index = pd.to_datetime(df_hotels.index)

    df_hotels.rename(columns={
        "VH101sa": "Occupancy (Seasonally Adjusted)",
        "VH102sa": "Mean Daily Rate (Seasonally Adjusted)",
        "VH103": "Revenue per Available Room"
    }, inplace=True)
    df_hotels = df_hotels.loc[df_hotels.index < cutoff_date].copy()
    df_hotels["Unit"] = "Hawaii"
    df_hotels["Mandatory Quarantine"] = (df_hotels.index >= quarantine_start).astype(int)

    if compute_growth:
        df_hotels = compute_annualized_growth(df_hotels)
        # Re-assign after growth since index is unchanged
        df_hotels["Mandatory Quarantine"] = (df_hotels.index >= quarantine_start).astype(int)
        df_hotels["Unit"] = "Hawaii"
        df_hotels.dropna(inplace=True)

    df_hotels.reset_index(inplace=True)
    df_hotels.rename(columns={"index": "Date"}, inplace=True)
    dfs["Hotels"] = df_hotels

    # --- Load Tourism data ---
    response_tourism = requests.get(urls["Tourism"])
    response_tourism.raise_for_status()
    data_tourism = response_tourism.json()
    dfs_tourism = []
    for s in data_tourism["data"]["series"]:
        df = pd.DataFrame(s["values"], index=pd.to_datetime(s["dates"]), columns=[s["columns"][0]])
        dfs_tourism.append(df)
    df_tourism = pd.concat(dfs_tourism, axis=1)

    # Ensure datetime index after concat
    if not pd.api.types.is_datetime64_any_dtype(df_tourism.index):
        df_tourism.index = pd.to_datetime(df_tourism.index)

    df_tourism.rename(columns={
        "VV101sa": "Visitor Arrivals (Seasonally Adjusted)",
        "VV102sa": "Visitor Days (Seasonally Adjusted)",
    }, inplace=True)
    df_tourism = df_tourism.loc[df_tourism.index < cutoff_date].copy()
    df_tourism["Unit"] = "Hawaii"
    df_tourism["Mandatory Quarantine"] = (df_tourism.index >= quarantine_start).astype(int)

    if compute_growth:
        df_tourism = compute_annualized_growth(df_tourism)
        df_tourism["Mandatory Quarantine"] = (df_tourism.index >= quarantine_start).astype(int)
        df_tourism["Unit"] = "Hawaii"
        df_tourism.dropna(inplace=True)

    df_tourism.reset_index(inplace=True)
    df_tourism.rename(columns={"index": "Date"}, inplace=True)
    dfs["Tourism"] = df_tourism

    # --- Load and merge FRED data ---
    df_lhe = pd.read_csv(urls["FRED_LHE"])
    df_lhe.columns = ["Date", "Leisure and Hospitality Employment YoY"]
    df_lhe["Date"] = pd.to_datetime(df_lhe["Date"])

    df_ui = pd.read_csv(urls["FRED_UI"])
    df_ui.columns = ["Date", "Initial Unemployment Claims YoY"]
    df_ui["Date"] = pd.to_datetime(df_ui["Date"])

    df_fred = pd.merge(df_lhe, df_ui, on="Date", how="outer")
    df_fred = df_fred[df_fred["Date"] < cutoff_date].copy()
    df_fred.sort_values("Date", inplace=True)
    df_fred.set_index("Date", inplace=True)
    df_fred["Unit"] = "Hawaii"
    df_fred["Mandatory Quarantine"] = (df_fred.index >= quarantine_start).astype(int)
    df_fred.dropna(inplace=True)
    df_fred.reset_index(inplace=True)

    dfs["FRED"] = df_fred

    if save_excel:
        with pd.ExcelWriter(filename) as writer:
            for sheet, df in dfs.items():
                df.to_excel(writer, sheet_name=sheet, index=False)

    return dfs
