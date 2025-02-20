from utils.dataget import get_weed_policies
from utils.datadisp import plot_policy_map
import os

# Path to the Excel file with cannabis policies
file_path = os.path.join(os.getcwd(), 'PolicyData', 'Cannabis', 'CannabisLaws.xlsx')

statelist = get_weed_policies(file_path)

remove_states = {"CA", "CO", "OR", "WA", "MA", "NV", "IL"}

purecontrols = list(set(statelist) - remove_states)

plot_policy_map(purecontrols, title="Legal Cannabis States", color="green", save_path="Figures/Chapter2/weed_map.png")
