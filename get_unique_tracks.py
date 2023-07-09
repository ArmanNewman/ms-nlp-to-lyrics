import os
import my_utils
import pandas as pd


def write_unique_tracks(chart_type: str):
    """Write the unique tracks from either older or this year's charts."""
    chart_suffix = {"old": "", "new": "_new"}[chart_type]
    os.chdir(f"mx_charts_csvs{chart_suffix}")
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

    if chart_type == "old":
        deduped_tracks.to_pickle("deduped_tracks.pickle")
    elif chart_type == "new":  # Select tracks that are not present in old tracks
        old_uris = pd.read_pickle("deduped_tracks.pickle").uri

        # Select tracks that are not present in old tracks
        deduped_tracks = deduped_tracks.loc[~deduped_tracks.uri.isin(old_uris), :]
        print(deduped_tracks)

    csv_destination = f"deduped_tracks{chart_suffix}.csv"
    # Check if the destination exists. If not, create it, else append
    file_exists = os.path.exists(csv_destination)
    if not file_exists:
        mode = "w"
        header = True
        deduped_tracks.to_csv(csv_destination, mode=mode, index=False, header=header)
        print(f"Destination {csv_destination} created")
        return
    else:
        mode = "a"
        header = False
        old_db = pd.read_csv(csv_destination)
        # Select only new songs
        new_tracks = deduped_tracks.loc[~deduped_tracks.uri.isin(old_db.uri)]
        # Check if there are any new records to append
        if new_tracks.empty:
            print("Nothing new to append.")
            return
        new_tracks.to_csv(csv_destination, mode=mode, index=False, header=header)
        print(f"Appended {new_tracks.shape[0]} to {csv_destination}")
        return


if __name__ == "__main__":
    # write_unique_tracks("old")
    write_unique_tracks("new")
