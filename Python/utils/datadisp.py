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

def plot_policy_map(state_groups, title, save_path=None):
    """
    Plots a U.S. map highlighting states based on treatment status with different colors.

    Parameters:
        state_groups (dict): Dictionary where keys are colors and values are lists of states.
        title (str): Title for the map.
        save_path (str, optional): Full path (including filename) where the plot will be saved.
                                  If None, the plot is not saved.
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
        sample_state = next(iter(state_groups.values()))[0]  # Get an example state from the first group
        key_col = "STUSPS" if len(sample_state) == 2 else "NAME"

        # Apply color mapping
        def assign_color(state):
            for color, states in state_groups.items():
                if state in states:
                    return color
            return "lightgray"  # Default for untreated states

        gdf["color"] = gdf[key_col].apply(assign_color)

        # Plot the map
        fig, ax = plt.subplots(figsize=(10, 6))
        gdf.plot(ax=ax, edgecolor="black", color=gdf["color"])

        # Customize the plot
        ax.set_title(title)
        ax.axis("off")  # Hide axis

        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, bbox_inches="tight")
        else:
            plt.show()
