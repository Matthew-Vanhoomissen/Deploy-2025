import pandas as pd 

df = pd.read_csv("../data/ticket_data.csv", low_memory=False)

desired_types = ["STR CLEAN", "PRK PROHIB", "PKG PROHIB", "NO PRK ZN", "DISOB SIGN", "NO PERMIT", "TMP PK RES", "METER DTN", "MTR OUT DT", "FIRE HYD", "RED ZONE", "YEL ZONE", "WHITE ZONE", "GREEN ZONE", "BLK BIKE L", "BL ZNE BLK", "SAFE/RED Z"]

df_filtered = df[df["violation_desc"].isin(desired_types)]

df_filtered.to_csv("../data/filtered_data.csv")
