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

file_path = r"Policy Data\Cannabis\CannabisLaws.xlsx"

policy_url = "https://datawrapper.dwcdn.net/Q43DW/150/dataset.csv"
restricted_statuses = [
    "Abortion banned",
    "Gestational limit between 6 and 12 weeks LMP",
]

plot_policy_map(get_treated_states(policy_url, restricted_statuses), "States with Abortion Bans", "#d40000")
