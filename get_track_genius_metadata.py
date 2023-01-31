import os
import time
import my_utils
from requests_html import HTMLSession
import pandas as pd

utc_now = pd.Timestamp.utcnow()
print(utc_now)
s_time = time.perf_counter()
s = HTMLSession()

# deduped_tracks = pd.read_pickle("deduped_tracks.pickle")
deduped_tracks = pd.read_csv("deduped_tracks.csv")

metadata_destination = "genius_metadata.pickle"

# Check if there is metadata to prevent querying twice
mtdta_exists = os.path.exists(metadata_destination)
if not mtdta_exists:
    # If it does not exist, then all tracks are new
    old_m = pd.DataFrame()
    new_tracks = deduped_tracks
if mtdta_exists:
    # If it does exist, then
    # check if there are new search_terms
    old_m = pd.read_pickle(metadata_destination)
    new_tracks = deduped_tracks.loc[~deduped_tracks.search_term.isin(old_m.search_term)]
    if new_tracks.empty:
        # If there aren't new search terms, exit program
        print("There aren't any new search terms for metadata")
        exit()

# Continue retrieving new search_terms' metadata
print(f"This script will call an api {new_tracks.shape[0]} times")
metadata_dfs = []
for df_idx, row in new_tracks.iterrows():
    df_i = my_utils.get_genius_metadata(s=s, search_term=row["search_term"])
    metadata_dfs.append(df_i)
metadata = pd.concat(metadata_dfs)

# Select only the first hit
metadata = metadata.loc[metadata.hit_idx == 0]

# Drop cases with duplicate URLs for lyrics
metadata.drop_duplicates(subset="url", keep="first", inplace=True)

# Select cases where 'lyrics' is present in the url
metadata = metadata.loc[metadata.url.str.contains("lyrics", regex=False)]

# If there was history, unite hist + new
if not old_m.empty:
    print(f"Current records in metadata: {old_m.shape[0]}")
    print(f"New records to add: {metadata.shape[0]}")
    metadata = pd.concat([old_m, metadata])

# Finally, store the results "w" mode
metadata.to_pickle(metadata_destination)
print(f"Written {metadata_destination} file with {metadata.shape[0]} records")
f_time = time.perf_counter()
elapsed = f_time - s_time
print(f"time elapsed: {str(elapsed)} seconds")
print("-" * 75)
