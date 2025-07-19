import requests
import pandas as pd
import matplotlib.pyplot as plt

def load_hawaii_data(save_excel=True, filename="hawaii_data.xlsx", compute_growth=True):
    urls = {
        "Hotels": "https://api.uhero.hawaii.edu/dvw/series/hotel?i=VH103,VH102sa,VH101sa&c=PVA11&f=M",
        "Tourism": "https://api.uhero.hawaii.edu/dvw/series/trend?i=VV101sa,VV102sa&m=MM102&d=DI10&f=M",
        "FRED": "https://fred.stlouisfed.org/graph/fredgraph.csv?&id=HILEIHN&cosd=1990-01-01&coed=2025-05-01&fq=Monthly&fam=avg&transformation=pc1"
    }

    dfs = {}

    def compute_annualized_growth(df, lag=12):
        numeric_cols = df.select_dtypes(include='number').columns
        growth_df = df.copy()
        growth_df[numeric_cols] = (df[numeric_cols] / df[numeric_cols].shift(lag)) - 1
        return growth_df

    # --- Load Hotels data ---
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
    df_hotels["Unit"] = "Hawaii"
    df_hotels["Mandatory Quarantine"] = (df_hotels.index >= "2020-03-01").astype(int)

    if compute_growth:
        df_hotels = compute_annualized_growth(df_hotels)
        df_hotels["Mandatory Quarantine"] = (df_hotels.index >= "2020-03-01").astype(int)
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
    df_tourism.rename(columns={
        "VV101sa": "Visitor Arrivals (Seasonally Adjusted)",
        "VV102sa": "Visitor Days (Seasonally Adjusted)",
    }, inplace=True)
    df_tourism = df_tourism.loc[df_tourism.index < "2021-01-01"].copy()
    df_tourism["Unit"] = "Hawaii"
    df_tourism["Mandatory Quarantine"] = (df_tourism.index >= "2020-03-01").astype(int)

    if compute_growth:
        df_tourism = compute_annualized_growth(df_tourism)
        df_tourism["Mandatory Quarantine"] = (df_tourism.index >= "2020-03-01").astype(int)
        df_tourism["Unit"] = "Hawaii"
        df_tourism.dropna(inplace=True)

    df_tourism.reset_index(inplace=True)
    df_tourism.rename(columns={"index": "Date"}, inplace=True)
    dfs["Tourism"] = df_tourism

    # --- Load and clean FRED data ---
    df_fred = pd.read_csv(urls["FRED"])
    date_col = df_fred.columns[0]
    df_fred[date_col] = pd.to_datetime(df_fred[date_col])
    df_fred.rename(columns={df_fred.columns[1]: "Leisure and Hospitality Employment YoY"}, inplace=True)
    df_fred = df_fred[df_fred[date_col] < "2021-01-01"].copy()
    df_fred.set_index(date_col, inplace=True)
    df_fred["Unit"] = "Hawaii"
    df_fred["Mandatory Quarantine"] = (df_fred.index >= "2020-03-01").astype(int)
    df_fred.dropna(inplace=True)

    df_fred.reset_index(inplace=True)
    df_fred.rename(columns={date_col: "Date"}, inplace=True)
    dfs["FRED"] = df_fred

    # --- Save to Excel ---
    if save_excel:
        with pd.ExcelWriter(filename) as writer:
            for sheet, df in dfs.items():
                df.to_excel(writer, sheet_name=sheet, index=False)

    return dfs


data = load_hawaii_data(filename="HawaiiData_Growth.xlsx", compute_growth=True)


# Define what to plot from each dataset
plot_columns = {
    "Tourism": ["Visitor Days (Seasonally Adjusted)", "Visitor Arrivals (Seasonally Adjusted)"],
    "Hotels": ["Occupancy (Seasonally Adjusted)", "Mean Daily Rate (Seasonally Adjusted)", "Revenue per Available Room"],
    "FRED": ["Leisure and Hospitality Employment YoY"]
}

# Create 3 rows × 2 columns of subplots
fig, axes = plt.subplots(3, 2, figsize=(10, 10), sharex=False)
#fig.suptitle("Hawaii Economic Indicators Over Time", fontsize=16)
axes = axes.flatten()

plot_idx = 0
for category, cols in plot_columns.items():
    df = data[category]
    for col in cols:
        ax = axes[plot_idx]
        ax.plot(df["Date"], df[col], color="black")
        ax.axvline(pd.to_datetime("2020-03-01"), color="red", linestyle="--", label="Mandatory Quarantine")
        ax.set_title(col, fontsize=14)
        #ax.set_ylim(-1, 1)
        ax.legend(loc="lower left", fontsize=12)
        ax.grid(True, linestyle="--", alpha=0.4)
        plot_idx += 1

# Remove any unused subplots
for i in range(plot_idx, len(axes)):
    fig.delaxes(axes[i])

plt.tight_layout(rect=[0, 0, 1, 0.95], h_pad=5)
plt.show()
