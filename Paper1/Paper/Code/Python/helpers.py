import requests
import pandas as pd

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
        
        # Combined Monthly FRED variables including Accommodation Employment
        "FRED_Monthly": (
            "https://fred.stlouisfed.org/graph/fredgraph.csv?"
            "id=HILEIHN,HIUR,LBSSA15,HIICLAIMS,SMU15000007072100001SA&"
            "cosd=1990-01-01&coed=2020-12-31&"
            "fq=Monthly&fam=avg&transformation=pc1&"
            "line_index=1,2,3,4,5"
        ),

        # Quarterly retail earnings data
        "FRED_Quarterly": (
            "https://fred.stlouisfed.org/graph/fredgraph.csv?"
            "id=HIERET&cosd=1998-01-01&coed=2020-12-31&"
            "fq=Quarterly&fam=avg&transformation=pc1"
        ),
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

    # --- Load Monthly FRED combined data ---
    df_fred_monthly = pd.read_csv(urls["FRED_Monthly"])
    df_fred_monthly.columns = [
        "Date",
        "Leisure and Hospitality Employment YoY",
        "Unemployment Rate YoY",
        "Labor Force Participation YoY (Hawaii)",
        "Initial Unemployment Claims YoY",
        "Accommodation Employment YoY"
    ]
    df_fred_monthly["Date"] = pd.to_datetime(df_fred_monthly["Date"])
    df_fred_monthly = df_fred_monthly[df_fred_monthly["Date"] < cutoff_date].copy()
    df_fred_monthly.sort_values("Date", inplace=True)
    df_fred_monthly["Unit"] = "Hawaii"
    df_fred_monthly["Mandatory Quarantine"] = (df_fred_monthly["Date"] >= quarantine_start).astype(int)
    df_fred_monthly.dropna(inplace=True)
    dfs["FRED_Monthly"] = df_fred_monthly

    # --- Load Quarterly FRED data (Retail Earnings) ---
    df_fred_quarterly = pd.read_csv(urls["FRED_Quarterly"])
    df_fred_quarterly.columns = ["Date", "Retail Earnings YoY"]
    df_fred_quarterly["Date"] = pd.to_datetime(df_fred_quarterly["Date"])
    df_fred_quarterly = df_fred_quarterly[df_fred_quarterly["Date"] < cutoff_date].copy()
    df_fred_quarterly.sort_values("Date", inplace=True)
    df_fred_quarterly["Unit"] = "Hawaii"
    df_fred_quarterly["Mandatory Quarantine"] = (df_fred_quarterly["Date"] >= quarantine_start).astype(int)
    df_fred_quarterly.dropna(inplace=True)
    dfs["FRED_Quarterly"] = df_fred_quarterly

    if save_excel:
        with pd.ExcelWriter(filename) as writer:
            for sheet, df in dfs.items():
                df.to_excel(writer, sheet_name=sheet, index=False)

    return dfs
