from utils.dataget import get_weed_policies
#import utils.datadisp as datadisp
import os
print(f"Current working directory: {os.getcwd()}")

# Path to the Excel file with cannabis policies
file_path = r"../../PolicyData/Cannabis/CannabisLaws.xlsx"

# Get states where cannabis is legal
cannabis_states = get_weed_policies(file_path)
print(cannabis_states)
# Plot the map
#datadisp.plot_policy_map(cannabis_states, "States with Legal Cannabis", "#008000")
