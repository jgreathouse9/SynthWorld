from utils.dataget import get_weed_policies
from utils.datadisp import plot_policy_map
import os

# Path to the Excel file with cannabis policies
file_path = os.path.join(os.getcwd(), 'PolicyData', 'Cannabis', 'CannabisLaws.xlsx')

# Get states where cannabis is legal
cannabis_states = get_weed_policies(file_path)

plot_policy_map(cannabis_states, "States with Legal Cannabis", "#008000")
