import os
import pandas as pd

# Print some stats or info for logging
now = pd.Timestamp.utcnow()
print(now)

# Read 3 data sources
tracks = pd.read_pickle("deduped_tracks.pickle")
mtdta = pd.read_pickle("genius_metadata.pickle")
lyrics_df = pd.read_pickle("lyrics.pickle")

# Join metadata with lyrics
mtd_lyrics = mtdta.loc[:, ["search_term", "url"]].merge(lyrics_df, how="left", on="url")

track_lyrics = tracks.merge(mtd_lyrics, how="left", on="search_term", validate="m:1")

# Clean the data to replace empty strings with NaN or Nulls
track_lyrics.loc[track_lyrics.lyrics == "", "lyrics"] = pd.NA

# Write results
destination = "deduped_tracks_lyrics.pickle"
file_exists = os.path.exists(destination)
if not file_exists:
    track_lyrics.to_pickle(destination)
    print(f"{destination} created with {track_lyrics.shape[0]} records")
else:
    # Emulate an UPSERT job
    old_v = pd.read_pickle(destination)
    # Select uris not present in the track_lyrics update
    old_no_update = old_v.loc[old_v.lyrics.notnull()]
    print("Rows that remain the same:", old_no_update.shape[0])

    # Select uris with new lyrics
    new_with_update = track_lyrics.loc[(~track_lyrics.uri.isin(old_no_update.uri))]
    if not new_with_update.empty:
        print("New rows to append:", new_with_update.shape[0])
        new_v = pd.concat([old_no_update, new_with_update])
        new_v.to_pickle(destination)
        print("End results:", new_v.shape[0])
    else:
        print("No new updates")

# Print some stats or info for logging
print("URIs with lyrics:")
data = pd.read_pickle(destination)
s = data.groupby(data.lyrics.notnull()).uri.nunique()
s_percent = s / s.sum()
my_summary = pd.DataFrame({"count": s, "percent": s_percent})
print(my_summary)
print("Total", my_summary["count"].sum())
print("-" * 75)
