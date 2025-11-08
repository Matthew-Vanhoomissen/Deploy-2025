import pandas as pd
import requests
import time
import csv
import io


def geocode_with_census_batch(input_csv, output_csv, batch_size=10000):
    """
    Geocode addresses using US Census Bureau Geocoding API (FREE, no limits!)
    Uses batch mode to process up to 10,000 addresses at once.
    Results can be stored permanently with no restrictions.
    
    No API key needed!
    """
    print("=" * 70)
    print("US CENSUS BUREAU GEOCODING - FREE & UNLIMITED")
    print("=" * 70)
    
    # Load data
    print(f"\n📂 Loading data from: {input_csv}")
    df = pd.read_csv(input_csv)
    print(f"✅ Total records: {len(df)}")
    
    # Get unique addresses
    unique_addresses = df['citation_location'].unique()
    print(f"🏠 Unique addresses found: {len(unique_addresses)}")
    
    # Create lookup dataframe
    lookup_df = pd.DataFrame({
        'address': unique_addresses,
        'latitude': None,
        'longitude': None
    })
    
    # Calculate number of batches needed
    num_batches = (len(unique_addresses) + batch_size - 1) // batch_size
    print(f"📦 Will process in {num_batches} batch(es) of up to {batch_size} addresses")
    print(f"⏱️  Estimated time: ~{num_batches * 2} minutes (Census API is fast!)")
    print(f"\n🚀 Starting geocoding...\n")
    
    successful = 0
    failed = 0
    
    # Process in batches
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(unique_addresses))
        batch_addresses = unique_addresses[start_idx:end_idx]
        
        print(f"📦 Processing batch {batch_num + 1}/{num_batches} ({len(batch_addresses)} addresses)")
        
        # Create CSV content for this batch
        # Format: Unique ID, Street address, City, State, ZIP
        batch_csv_lines = []
        for i, address in enumerate(batch_addresses):
            # Add San Francisco, CA to each address
            batch_csv_lines.append(f"{i},{address},San Francisco,CA,")
        
        batch_csv_content = "\n".join(batch_csv_lines)
        
        try:
            # Submit batch to Census API
            url = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
            
            files = {
                'addressFile': ('addresses.csv', batch_csv_content, 'text/csv')
            }
            
            data = {
                'benchmark': 'Public_AR_Current'
            }
            
            response = requests.post(url, files=files, data=data, timeout=120)
            response.raise_for_status()
            
            # Parse the response using CSV reader (handles quoted fields properly!)
            csv_reader = csv.reader(io.StringIO(response.text))
            
            batch_successful = 0
            batch_failed = 0
            
            for row in csv_reader:
                if len(row) >= 6:
                    try:
                        idx = int(row[0])
                        match_status = row[2]
                        
                        if match_status == "Match":
                            # Coordinates are in row[5] as "longitude,latitude"
                            coords_str = row[5]
                            
                            if coords_str and ',' in coords_str:
                                lon_str, lat_str = coords_str.split(',')
                                lon = float(lon_str.strip())
                                lat = float(lat_str.strip())
                                
                                # Update lookup table
                                address = batch_addresses[idx]
                                lookup_df.loc[lookup_df['address'] == address, 'latitude'] = lat
                                lookup_df.loc[lookup_df['address'] == address, 'longitude'] = lon
                                
                                batch_successful += 1
                                successful += 1
                            else:
                                batch_failed += 1
                                failed += 1
                        else:
                            batch_failed += 1
                            failed += 1
                            
                    except (ValueError, IndexError) as e:
                        print(f"   ⚠️  Parse error: {e}")
                        batch_failed += 1
                        failed += 1
                        continue
            
            print(f"   ✓ Batch complete: {batch_successful} successful, {batch_failed} failed")
            print(f"   📊 Running totals: {successful} successful, {failed} failed")
            
            # Save progress after each batch
            lookup_df.to_csv(output_csv, index=False)
            print(f"   💾 Progress saved to {output_csv}")
            
            # Brief pause between batches to be respectful
            if batch_num < num_batches - 1:
                time.sleep(2)
                
        except Exception as e:
            print(f"   ❌ Error processing batch: {e}")
            failed += len(batch_addresses)
    
    # Final save
    lookup_df.to_csv(output_csv, index=False)
    
    print(f"\n" + "=" * 70)
    print("✅ GEOCODING COMPLETE!")
    print("=" * 70)
    print(f"✓ Successful: {successful}")
    print(f"✗ Failed: {failed}")
    print(f"📍 Addresses with coordinates: {lookup_df['latitude'].notna().sum()}/{len(lookup_df)}")
    print(f"💾 Saved to: {output_csv}")
    print("=" * 70)
    
    return lookup_df


# ============================================================================
# USAGE
# ============================================================================

if __name__ == "__main__":

    # Process 50,000 addresses in 5 batches of 10,000
    INPUT_CSV = "../data/filtered_data.csv"
    OUTPUT_CSV = "../data/location_data.csv"

    lookup_table = geocode_with_census_batch(
        input_csv=INPUT_CSV,
        output_csv=OUTPUT_CSV
    )

# Done! Your lookup table is ready.