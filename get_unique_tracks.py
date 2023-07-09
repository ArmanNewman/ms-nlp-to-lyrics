import os
import my_utils
import pandas as pd

os.chdir("mx_charts_csvs")
csv_files = os.listdir()
csv_files = sorted(csv_files, reverse=True)
charts_list = []
for csv in csv_files:
    print(csv)
    chart_i = pd.read_csv(csv)
    charts_list.append(chart_i)
charts = pd.concat(charts_list, ignore_index=True)
os.chdir("..")

# Deduplicate uri, artist, track
select_columns = ["uri", "artist_names", "track_name"]
deduped_tracks = charts.loc[:, select_columns].drop_duplicates(subset="uri")
print(f"Total unique tracks: {deduped_tracks.shape[0]}")

# Simplify the search term
main_artist = deduped_tracks.artist_names.apply(lambda x: x.split(",")[0])

# Clean featurings inside parenthesis or brackets
simplified_title = deduped_tracks.track_name.apply(my_utils.simplify_track_title)

deduped_tracks["search_term"] = simplified_title + " by " + main_artist
deduped_tracks["search_term"] = deduped_tracks.search_term.str.lower()

deduped_tracks.to_pickle("deduped_tracks.pickle")

csv_destination = "deduped_tracks.csv"
# Check if the destination exists. If not, create it, else append
file_exists = os.path.exists(csv_destination)
if not file_exists:
    mode = "w"
    header = True
    deduped_tracks.to_csv(csv_destination, mode=mode, index=False, header=header)
    print(f"Destination {csv_destination} created")
else:
    mode = "a"
    header = False
    old_db = pd.read_csv(csv_destination)
    # Select only new songs
    new_tracks = deduped_tracks.loc[~deduped_tracks.uri.isin(old_db.uri)]
    # Check if there are any new records to append
    if not new_tracks.empty:
        new_tracks.to_csv(csv_destination, mode=mode, index=False, header=header)
        print(f"Appended {new_tracks.shape[0]} to {csv_destination}")
    else:
        print("Nothing new to append.")
