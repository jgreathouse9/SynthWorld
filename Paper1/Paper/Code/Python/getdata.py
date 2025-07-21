import os
from helpers import load_hawaii_data

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # up two levels
data_path = os.path.join(base_dir, "Data", "HawaiiData.xlsx")

load_hawaii_data(save_excel=True,filename=data_path)
