import pandas as pd
from mlsynth import SHC

# https://masks4all.co/what-countries-require-masks-in-public/

# Define the path (raw string recommended for Windows paths with backslashes)
file_path = r"C:\The Shop\mlsynth\app\HawaiiData_Growth.xlsx"

# Read the "Hotels" sheet
df = pd.read_excel(file_path, sheet_name="Tourism")
df.rename(columns={df.columns[0]: "Time"}, inplace=True)
df["Unit"] = "Hawaii"

config = {
    "df": df,
    "outcome": df.columns[1],
    "treat": "Border Closure",
    "unitid": "Unit",
    "time": df.columns[0],
    "display_graphs": True,
    "save": False,
    "counterfactual_color": ["blue"], "m": 12*8
}

result = SHC(config).fit()
