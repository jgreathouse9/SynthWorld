import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import tempfile
import requests
import zipfile
import os
import matplotlib

file_path = r"Policy Data\Cannabis\CannabisLaws.xlsx"


# Example usage
file_path = r"C:\The Shop\CannabisLaws.xlsx"
common_policy = get_unique_policies(file_path)
datadisp.plot_policy_map(common_policy, "States with Legal Cannabis", "#008000")
