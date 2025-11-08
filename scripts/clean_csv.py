import pandas as pd 

df = pd.read_csv("../data/location_data.csv", low_memory=False)

df_cleaned = df.dropna()
df_cleaned.to_csv("../data/cleaned_location_data.csv")