from utils.dataget import get_weed_policies
from utils.datadisp import plot_policy_map
import os

# Path to the Excel file with cannabis policies
file_path = os.path.join(os.getcwd(), 'PolicyData', 'Cannabis', 'CannabisLaws.xlsx')

statelist = get_weed_policies(file_path)

print(f"The number of control states is {len(statelist)}")

plot_policy_map(statelist, title="Legal Cannabis States", color="green", save_path="Figures/Chapter2/weed_map.png")
