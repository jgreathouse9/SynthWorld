import geopandas as gpd
import matplotlib.pyplot as plt
import tempfile
import requests
import zipfile
import os
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

# U.S. shapefile URL
ZIP_URL = "https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_state_20m.zip"

def plot_policy_map(treated_states, title, color, save_path=None):
    """
    Plots a U.S. map highlighting states with a specific policy and optionally saves it to a file.

    Parameters:
        treated_states (list): List of state abbreviations or full names based on dataset.
        title (str): Title for the map.
        color (str): Color for the treated states.
        save_path (str, optional): Path to save the plot (including file name). If None, the plot is not saved.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download and extract the shapefile
        zip_path = os.path.join(tmpdir, "shapefile.zip")
        response = requests.get(ZIP_URL)
        with open(zip_path, "wb") as f:
            f.write(response.content)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmpdir)

        # Read shapefile
        shp_path = os.path.join(tmpdir, "cb_2018_us_state_20m.shp")
        gdf = gpd.read_file(shp_path)

        # Exclude Puerto Rico, Hawaii, and Alaska
        gdf = gdf[~gdf["STATEFP"].isin(["02", "15", "72"])]

        # Determine key column (abbreviation vs. full name)
        key_col = "STUSPS" if len(treated_states[0]) == 2 else "NAME"

        # Apply color mapping
        gdf["color"] = gdf[key_col].apply(lambda x: color if x in treated_states else "lightgray")

        # Plot the map
        fig, ax = plt.subplots(figsize=(10, 6))
        gdf.plot(ax=ax, edgecolor="black", color=gdf["color"])

        # Customize the plot
        ax.set_title(title)
        ax.axis("off")  # Hide axis

        if fig_name:
            # Ensure the directory exists before saving the plot
            save_path = os.path.join("SynthWorld", "Figures", "Chapter2", fig_name)  # Full path
            os.makedirs(os.path.dirname(save_path), exist_ok=True)  # Create directories if needed
            # Save the plot to the specified path
            plt.savefig(save_path, bbox_inches="tight")
        else:
            # Show the plot if no fig_name is specified
            plt.show()
