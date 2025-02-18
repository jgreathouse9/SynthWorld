import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import tempfile
import requests
import zipfile
import os
from io import StringIO
import matplotlib

# Your custom theme settings
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


# URLs for datasets
zip_url = "https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_state_20m.zip"
policy_url = "https://datawrapper.dwcdn.net/Q43DW/150/dataset.csv"

# Custom headers to avoid 403 error
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# Function to get treated state names by requesting the policy data and processing it
def get_treated_states(policy_url, restricted_statuses):
    # Make the request with headers
    response = requests.get(policy_url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Read the CSV content into a Pandas DataFrame
        policydf = pd.read_csv(StringIO(response.text), sep="\t")

        # Filter states with restricted abortion policies
        return policydf[policydf["Status of Abortion"].isin(restricted_statuses)]["State"].tolist()
    else:
        print(f"Failed to fetch data: {response.status_code}")
        return []


# Define restricted abortion statuses
restricted_statuses = ["Abortion banned", "Gestational limit between 6 and 12 weeks LMP"]

# Get the list of treated states
treated_states = get_treated_states(policy_url, restricted_statuses)

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

    # Create a color column based on the abortion policy
    gdf["color"] = gdf["NAME"].apply(lambda x: "#d40000" if x in treated_states else "lightgray")

    # Plot the map
    fig, ax = plt.subplots(figsize=(10, 6))
    gdf.plot(ax=ax, edgecolor="black", color=gdf["color"])

    # Customize the plot
    ax.set_title("States with Abortion Bans")
    ax.axis("off")  # Hide axis

    plt.show()
