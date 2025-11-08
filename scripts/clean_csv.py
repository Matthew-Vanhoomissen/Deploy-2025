import pandas as pd
import numpy as np

# Load ticket dataset
tickets = pd.read_csv("../data/filtered_data.csv", skiprows=0)
coords = pd.read_csv("../data/cleaned_location_data.csv")

# Standardize address columns for merge
tickets['citation_location'] = tickets['citation_location'].astype(str).str.strip().str.upper()
coords['address'] = coords['address'].astype(str).str.strip().str.upper()

# Merge on address
merged_df = pd.merge(
    tickets,
    coords[['address', 'latitude', 'longitude']],
    left_on='citation_location',
    right_on='address',
    how='left'
)

# Drop redundant column
merged_df = merged_df.drop(columns=['address'])

# Clean column names
merged_df.columns = merged_df.columns.str.strip().str.lower()

# Fix _x/_y columns if any
if 'latitude_y' in merged_df.columns:
    merged_df['latitude'] = merged_df['latitude_y']
    merged_df['longitude'] = merged_df['longitude_y']
    merged_df = merged_df.drop(columns=[c for c in merged_df.columns if c.endswith('_x') or c.endswith('_y')])

# Convert latitude / longitude to numeric (coerce invalid values to NaN)
merged_df['latitude'] = pd.to_numeric(merged_df['latitude'], errors='coerce')
merged_df['longitude'] = pd.to_numeric(merged_df['longitude'], errors='coerce')

# Drop rows where lat or lon is NaN
merged_df = merged_df.dropna(subset=['latitude', 'longitude'])

# Check results
print(merged_df[['citation_location', 'latitude', 'longitude']].head())
print(f"Total rows after dropping missing coords: {len(merged_df)}")

# Save merged dataset
merged_df.to_csv("../data/tickets_with_coords.csv", index=False)