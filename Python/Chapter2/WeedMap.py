from utils.dataget import get_weed_policies
#import utils.datadisp as datadisp

# Path to the Excel file with cannabis policies
file_path = r"PolicyData\CannabisLaws.xlsx"

# Get states where cannabis is legal
cannabis_states = get_weed_policies(file_path)
print(cannabis_states)
# Plot the map
#datadisp.plot_policy_map(cannabis_states, "States with Legal Cannabis", "#008000")
