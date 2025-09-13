import pickle
from mlsynth.utils.datautils import dataprep
from mlsynth.utils.helperutils import sc_diagplot
from mlsynth import FSCM, PDA, CLUSTERSC
# Replace with your actual pickle file path if different
pickle_file_path = 'employment_growth_data.pkl'

with open(pickle_file_path, 'rb') as f:
    loaded_data = pickle.load(f)

# Extract the dataframes
df_msa = loaded_data['MSA']
df_csa = loaded_data['CSA']

config = {
    "df": df_msa,
    "outcome": "YoY_Emp",
    "treat": "Key to NYC",
    "unitid": "MSA",
    "time":  "Date",
    "display_graphs": True,
    "save": False,
    "counterfactual_color": ["red", "blue"], "cluster": False} # FSCM: , "use_augmented":True, "full_selection": False, "selection_fraction": 0.3

arco = CLUSTERSC(config).fit()
