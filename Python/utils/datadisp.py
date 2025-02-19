import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import tempfile
import requests
import zipfile
import os
from io import StringIO
import matplotlib

# Custom theme settings

jared_theme = {
    "axes.grid": False,
    "grid.linestyle": "-",
    "grid.color": "black",
    "legend.framealpha": 1,
    "legend.facecolor": "white",
    "legend.shadow": True,
    "legend.fontsize": 14,
    "legend.title_fontsize": 16,
    "xtick.labelsize": 11,
    "ytick.labelsize": 14,
    "axes.labelsize": 14,
    "axes.titlesize": 20,
    "figure.dpi": 120,
    "axes.facecolor": "white",
    "figure.figsize": (10, 6),
}

matplotlib.rcParams.update(jared_theme)

# URL for U.S. shapefile

ZIP_URL = "https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_state_20m.zip"


def get_unique_policies(file_path, sheet_name="for stata"):
    """
    Extracts states with legalized cannabis policies from an Excel file.

    Parameters:
        file_path (str): Path to the Excel file.
        sheet_name (str): Sheet name containing the policy data.

    Returns:
        list: List of state abbreviations where cannabis is legal.
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    df = df.drop(index=range(51, 57))  # Remove extra rows
    df = df.dropna(
        subset=["dispensary_open_date"]
    )  # Keep rows with a dispensary open date
    df = df.sort_values(by="dispensary_open_date")  # Sort by date
    df = df[["state", "st", "dispensary_open_date"]]
    df = df[~df["st"].isin(["AK", "HI"])]  # Remove AK and HI
    return df.iloc[:, 1].unique().tolist()  # Return state abbreviations


def get_treated_states(policy_url, restricted_statuses):
    """
    Fetches states with restricted abortion policies from an online dataset.

    Parameters:
        policy_url (str): URL to the policy dataset (CSV format).
        restricted_statuses (list): List of policy labels to filter.

    Returns:
        list: List of state names where abortion is banned or restricted.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(policy_url, headers=headers)
    if response.status_code == 200:
        policydf = pd.read_csv(StringIO(response.text), sep="\t")
        return policydf[policydf["Status of Abortion"].isin(restricted_statuses)][
            "State"
        ].tolist()
    else:
        print(f"Failed to fetch data: {response.status_code}")
        return []


def plot_policy_map(treated_states, title, color):
    """
    Plots a U.S. map highlighting states with a specific policy.

    Parameters:
        treated_states (list): List of state abbreviations or names based on dataset.
        title (str): Title for the map.
        color (str): Color for the treated states.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download and extract the shapefile

        zip_path = os.path.join(tmpdir, "shapefile.zip")
        response = requests.get(ZIP_URL)
        with open(zip_path, "wb") as f:
            f.write(response.content)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmpdir)
        # Find and read the shapefile

        shp_path = os.path.join(tmpdir, "cb_2018_us_state_20m.shp")
        gdf = gpd.read_file(shp_path)

        # Exclude Puerto Rico, Hawaii, and Alaska

        gdf = gdf[~gdf["STATEFP"].isin(["02", "15", "72"])]

        # Handle state abbreviations vs. full names

        key_col = "STUSPS" if len(treated_states[0]) == 2 else "NAME"

        # Apply coloring based on treated states

        gdf["color"] = gdf[key_col].apply(
            lambda x: color if x in treated_states else "white"
        )

        # Plot the map

        fig, ax = plt.subplots(figsize=(10, 6))
        gdf.plot(ax=ax, edgecolor="black", color=gdf["color"])

        # Customize the plot

        ax.set_title(title)
        ax.axis("off")  # Hide axis

        plt.show()


# Example usage

file_path = r"Policy Data\CannabisLaws.xlsx"

plot_policy_map(get_unique_policies(file_path), "States with Legal Cannabis", "#008000")

policy_url = "https://datawrapper.dwcdn.net/Q43DW/150/dataset.csv"
restricted_statuses = [
    "Abortion banned",
    "Gestational limit between 6 and 12 weeks LMP",
]

plot_policy_map(get_treated_states(policy_url, restricted_statuses), "States with Abortion Bans", "#d40000")
