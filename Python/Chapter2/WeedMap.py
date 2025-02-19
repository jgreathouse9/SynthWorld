from utils.dataget import get_weed_policies
from utils.datadisp import plot_policy_map
import os

# Path to the Excel file with cannabis policies
file_path = os.path.join(os.getcwd(), 'PolicyData', 'Cannabis', 'CannabisLaws.xlsx')


plot_policy_map(get_weed_policies(file_path), title="Legal Cannabis States", color="green", save_path="Figures/Chapter2/weed_map.png")
