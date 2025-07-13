import requests
import pandas as pd


def load_hawaii_data(save_excel=True, filename="hawaii_data.xlsx", compute_growth=True):
    urls = {
        "Hotels": "https://api.uhero.hawaii.edu/dvw/series/hotel?i=VH103,VH102sa,VH101sa&c=PVA11&f=M",
        "Tourism": "https://api.uhero.hawaii.edu/dvw/series/trend?i=VV101sa,VV102sa&m=MM102&d=DI10&f=M"
    }

    dfs = {}

    def compute_annualized_growth(df, lag=12):
        ratio = df / df.shift(lag)
        if lag == 12:
            growth = ratio - 1
        else:
            growth = ratio ** (12 / lag) - 1
        return growth

    # Load Hotels data
    response_hotel = requests.get(urls["Hotels"])
    response_hotel.raise_for_status()
    data_hotel = response_hotel.json()
    dfs_hotel = []
    for s in data_hotel["data"]["series"]:
        df = pd.DataFrame(s["values"], index=pd.to_datetime(s["dates"]), columns=[s["columns"][0]])
        dfs_hotel.append(df)
    df_hotels = pd.concat(dfs_hotel, axis=1)
    df_hotels.rename(columns={
        "VH101sa": "Occupancy (Seasonally Adjusted)",
        "VH102sa": "Mean Daily Rate (Seasonally Adjusted)",
        "VH103": "Revenue per Available Room"
    }, inplace=True)
    df_hotels = df_hotels.loc[df_hotels.index < "2021-01-01"].copy()
    df_hotels["Border Closure"] = (df_hotels.index >= "2020-04-01").astype(int)

    if compute_growth:
        df_hotels = compute_annualized_growth(df_hotels)
        df_hotels["Border Closure"] = (df_hotels.index >= "2020-04-01").astype(int)
        df_hotels.dropna(inplace=True)

    dfs["Hotels"] = df_hotels

    # Load Tourism data
    response_tourism = requests.get(urls["Tourism"])
    response_tourism.raise_for_status()
    data_tourism = response_tourism.json()
    dfs_tourism = []
    for s in data_tourism["data"]["series"]:
        df = pd.DataFrame(s["values"], index=pd.to_datetime(s["dates"]), columns=[s["columns"][0]])
        dfs_tourism.append(df)
    df_tourism = pd.concat(dfs_tourism, axis=1)
    df_tourism.rename(columns={
        "VV101sa": "Visitor Arrivals (Seasonally Adjusted)",
        "VV102sa": "Visitor Days (Seasonally Adjusted)",
    }, inplace=True)
    df_tourism = df_tourism.loc[df_tourism.index < "2021-01-01"].copy()
    df_tourism["Border Closure"] = (df_tourism.index >= "2020-04-01").astype(int)

    if compute_growth:
        df_tourism = compute_annualized_growth(df_tourism)
        df_tourism["Border Closure"] = (df_tourism.index >= "2020-04-01").astype(int)
        df_tourism.dropna(inplace=True)

    dfs["Tourism"] = df_tourism

    if save_excel:
        with pd.ExcelWriter(filename) as writer:
            dfs["Hotels"].to_excel(writer, sheet_name="Hotels")
            dfs["Tourism"].to_excel(writer, sheet_name="Tourism")

    return dfs


data = load_hawaii_data(filename="HawaiiData_Growth.xlsx", compute_growth=True)
