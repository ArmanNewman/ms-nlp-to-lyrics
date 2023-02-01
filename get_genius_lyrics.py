import os
import time
from requests_html import HTMLSession
import pandas as pd
import my_utils

utc_now = pd.Timestamp.utcnow()
print(utc_now)
s_time = time.perf_counter()
s = HTMLSession()

metadata = pd.read_pickle("genius_metadata.pickle")

lyrics_destination = "lyrics.pickle"

# Check if there are lyrics to prevent querying twice
lyrics_exists = os.path.exists(lyrics_destination)
if not lyrics_exists:
    # If it does not exist, then all tracks are new
    old_lyr = pd.DataFrame()
    new_tracks = metadata
if lyrics_exists:
    # If it does exist, then
    # check if there are new urls
    old_lyr = pd.read_pickle(lyrics_destination)
    new_tracks = metadata.loc[~metadata.url.isin(old_lyr.url)]
    if new_tracks.empty:
        # If there aren't new urls, exit program
        print("There aren't any new urls for lyrics")
        exit()

# Retrieve the Lyrics
lyrics_list = []
print("Total records to query lyrics:", new_tracks.shape[0])
for i, row in new_tracks.iterrows():
    lyrics_record = my_utils.get_lyrics(s=s, lyrics_url=row["url"])
    if lyrics_record:
        lyrics_list.append(lyrics_record)
    elif not lyrics_record:
        print(row["url"], "Does not have lyrics in Genius site")

lyrics_df = pd.DataFrame(lyrics_list)

# If there was history, unite hist + new
if not old_lyr.empty:
    print(f"Current records in lyrics: {old_lyr.shape[0]}")
    print(f"New records to add: {lyrics_df.shape[0]}")
    lyrics_df = pd.concat([old_lyr, lyrics_df])

# Finally, store the results "w" mode
lyrics_df.to_pickle(lyrics_destination)
print(f"Written {lyrics_destination} file with {lyrics_df.shape[0]} records")
f_time = time.perf_counter()
elapsed = f_time - s_time
print(f"time elapsed: {str(elapsed)} seconds")
print("-" * 75)
