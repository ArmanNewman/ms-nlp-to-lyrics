import os
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
deduped_tracks["search_term"] = (
    deduped_tracks.artist_names + " " + deduped_tracks.track_name
)
deduped_tracks["search_term"] = deduped_tracks.search_term.str.lower()

deduped_tracks.to_clipboard(index=False)
deduped_tracks.to_pickle("deduped_tracks.pickle")
deduped_tracks.to_csv("deduped_tracks.csv", index=False)
