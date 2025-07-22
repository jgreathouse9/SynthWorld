import os
from helpers import load_hawaii_data, get_taxdata

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # up two levels
data_pathtourism = os.path.join(base_dir, "Data", "HawaiiData.xlsx")
data_pathtax = os.path.join(base_dir, "Data", "HawaiiData.xlsx")

load_hawaii_data(save_excel=True,filename=data_pathtourism)

get_taxdata(save_excel=True,filename=data_pathtax)
