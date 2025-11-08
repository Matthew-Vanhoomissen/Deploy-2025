import pandas as pd
from sodapy import Socrata
from dotenv import load_dotenv
import os

load_dotenv()

APP_TOKEN = os.getenv("DATASF_APP_TOKEN")

# Unauthenticated client only works with public data sets. Note 'None'
# in place of application token, and no username or password:
client = Socrata("data.sfgov.org", APP_TOKEN)

# Example authenticated client (needed for non-public datasets):
# client = Socrata(data.sfgov.org,
#                  MyAppToken,
#                  username="user@example.com",
#                  password="AFakePassword")

# First 2000 results, returned as JSON from API / converted to Python list of
# dictionaries by sodapy.
results = client.get("ab4h-6ztd", limit=20)

# Convert to pandas DataFrame
results_df = pd.DataFrame.from_records(results)
results_df.to_csv("../data/ticket_data.csv")
