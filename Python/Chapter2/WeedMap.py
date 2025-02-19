import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import tempfile
import requests
import zipfile
import os
import matplotlib

file_path = r"Policy Data\Cannabis\CannabisLaws.xlsx"


plot_policy_map(get_unique_policies(file_path), "States with Legal Cannabis", "#008000")

def get_unique_policies(file_path, sheet_name="for stata"):
    # Load the Excel file
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    # Drop rows 52 to 57 (adjusting for 0-based indexing)
    df = df.drop(index=range(51, 57))

    # Drop rows where 'dispensary_open_date' is missing
    df = df.dropna(subset=['dispensary_open_date'])

    # Sort by 'dispensary_open_date'
    df = df.sort_values(by='dispensary_open_date')

    # Keep only specified columns
    df = df[['state', 'st', 'dispensary_open_date']]

    # Drop rows where 'st' is in ["AK", "HI"]
    df = df[~df['st'].isin(["AK", "HI"])]

    # Get unique values from the second column ('st') as a list
    return df.iloc[:, 1].unique().tolist()

# Example usage
file_path = r"C:\The Shop\CannabisLaws.xlsx"
common_policy = get_unique_policies(file_path)

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
    "figure.figsize": (10, 5.5),
}

matplotlib.rcParams.update(jared_theme)

# URL for U.S. shapefile
zip_url = "https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_state_20m.zip"

# Create a temporary directory
with tempfile.TemporaryDirectory() as tmpdir:
    # Download the ZIP file
    zip_path = os.path.join(tmpdir, "shapefile.zip")
    response = requests.get(zip_url)
    with open(zip_path, "wb") as f:
        f.write(response.content)

    # Extract the ZIP file
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(tmpdir)

    # Find the .shp file inside the extracted folder
    shp_path = os.path.join(tmpdir, "cb_2018_us_state_20m.shp")

    # Read the shapefile with geopandas
    gdf = gpd.read_file(shp_path)

    # Exclude Puerto Rico, Hawaii, and Alaska
    gdf = gdf[~gdf["STATEFP"].isin(["02", "15", "72"])]

    # Assign color based on cannabis legalization
    gdf["color"] = gdf["STUSPS"].apply(lambda x: "#008000" if x in common_policy else "lightgray")  # Green for legal states

    # Plot the map
    fig, ax = plt.subplots(figsize=(10, 6))
    gdf.plot(ax=ax, edgecolor="black", color=gdf["color"])

    # Customize the plot
    ax.set_title("States with Legalized Cannabis")
    ax.axis("off")  # Hide axis

    plt.show()

