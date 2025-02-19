import utils.dataget as dataget
import utils.datadisp as datadisp

# Path to the Excel file with cannabis policies
file_path = r"C:\The Shop\CannabisLaws.xlsx"

# Get states where cannabis is legal
cannabis_states = dataget.get_weed_policies(file_path)

# Plot the map
datadisp.plot_policy_map(cannabis_states, "States with Legal Cannabis", "#008000")
