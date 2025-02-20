from utils.dataget import get_weed_policies
from utils.datadisp import plot_policy_map
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

# Path to the Excel file with cannabis policies
file_path = os.path.join(os.getcwd(), 'PolicyData', 'Cannabis', 'CannabisLaws.xlsx')

statelist = get_weed_policies(file_path)

remove_states = {"CA", "CO", "OR", "WA", "MA", "NV", "IL"}

print(f"The number of pretreated states is {len(remove_states)}")

purecontrols = list(set(statelist) - remove_states)

print(f"The number of donor states is {len(remove_states)-1}")

# Dictionary of colors and state groups
state_groups = {
    "green": purecontrols,       # Donor states
    "lightgreen": remove_states  # Previously treated states (Shops Open)
}

# Custom legend labels
legend_labels = {
    "green": "Donor States",
    "lightgreen": "Shops Open",
    "lightgray": "No MML"
}

plot_policy_map(state_groups, title="Cannabis Legality", legend_labels=legend_labels, save_path="Figures/Chapter2/WeedLegalityStates.png")
