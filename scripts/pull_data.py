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
results = client.get("ab4h-6ztd", where="citation_issued_datetime >= '2025-10-01T00:00:00'", limit=200000)
result = client.get(
    "ab4h-6ztd",
    select="max(citation_issued_datetime)"
)
print(result)
# Convert to pandas DataFrame
df = pd.DataFrame.from_records(results)

df["citation_issued_datetime"] = pd.to_datetime(df["citation_issued_datetime"], errors="coerce")
df["year"] = df["citation_issued_datetime"].dt.year

df_2025 = df[df["year"] == 2025]

df_2025.to_csv("../data/ticket_data.csv")
