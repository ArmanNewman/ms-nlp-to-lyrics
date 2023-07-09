import os
import time
import my_utils
from requests_html import HTMLSession
import pandas as pd


def get_lyrics_for_charting_tracks(chart_type: str) -> None:
    """Executes the retrieval of lyrics for charting tracks considering 3 scenarios:
    - Case 1: There is no prior data, so all is new (OK)
    - Case 2: There is old data, the new data has NO lyrics updates (OK)
    - Case 3: There is old data, the new data has lyrics updates (OK)
    """
    utc_now = pd.Timestamp.utcnow()
    print(utc_now)
    s_time = time.perf_counter()
    s = HTMLSession()

    rapidapi_key = os.environ.get("RAPID_API_KEY")

    chart_suffix = {"old": "", "new": "_new"}[chart_type]
    input_charts = pd.read_csv(f"deduped_tracks{chart_suffix}.csv")
    destination = f"chart_lyrics{chart_suffix}.pickle"

    # Check if the destination exists to prevent querying twice
    destination_exists = os.path.exists(destination)
    target_cols = [
        "uri",
        "artist_names",
        "track_name",
        "search_term",
        "lyrics_source",
        "lyrics",
    ]
    # CASE 1: All is new
    if not destination_exists:
        # If it does not exist, then all tracks are new
        lyrics_list = []
        for _, row in input_charts.iterrows():
            lyr = my_utils.get_lyrics(
                s=s,
                search_term=row["search_term"],
                song_title=my_utils.simplify_track_title(row["track_name"]),
                api_key=rapidapi_key,
            ).assign(uri=row["uri"], track_name=row["track_name"])
            lyrics_list.append(lyr)
        chart_lyrics = pd.concat(lyrics_list)[target_cols].set_index("uri")

        # Finally, store the results "w" mode
        chart_lyrics.to_pickle(destination)
        print(f"Written {destination} file with {chart_lyrics.shape[0]} records")
        f_time = time.perf_counter()
        elapsed = f_time - s_time
        print(f"time elapsed: {str(elapsed)} seconds")
        print("-" * 75)
        return

    # CASE 2: There is prior data, no lyrics updates
    # Continue below assuming the destination exists
    elif destination_exists:
        # If it does exist, then
        # check if there are new search_terms
        old_data = pd.read_pickle(destination).replace(
            {"lyrics": {"": pd.NA}}
        )  # Convert empty strings into NaNs in the lyrics column
        assert not old_data.empty

        # Check if there are new tracks where the old data did not contain lyrics
        new_tracks = input_charts.set_index("uri").loc[old_data.lyrics.isna()]
        if new_tracks.empty:
            # If there aren't new search terms, exit program
            print(f"There aren't any new search terms for {destination}")
            return

        # CASE 3: There is prior data with empty or null lyrics AND the new data contains updates
        print(f"This script will call an api to search {new_tracks.shape[0]} songs")
        metadata_dfs = []

        for uri, row in new_tracks.iterrows():
            df_i = my_utils.get_lyrics(
                s=s,
                search_term=row["search_term"],
                song_title=my_utils.simplify_track_title(row["track_name"]),
                api_key=rapidapi_key,
            )
            if df_i is not None:
                df_i["uri"] = uri
                df_i["track_name"] = row["track_name"]
                metadata_dfs.append(df_i)
        # Drop cases with duplicate Spotify URIs
        new_lyrics = (
            pd.concat(metadata_dfs)
            .drop_duplicates(subset="uri", keep="first")[target_cols]
            .replace({"lyrics": {"": pd.NA}})
            .dropna(subset="lyrics")
            .set_index("uri")
        )
        assert not new_lyrics.empty

        # Unite hist + new
        print(
            f"Current records with lyrics in {destination}: {old_data.loc[~old_data.lyrics.isna()].shape[0]}"
        )
        print(f"New records to add: {new_lyrics.shape[0]}")
        old_data.update(new_lyrics, join="left", overwrite=True)

        # Finally, store the results "w" mode
        old_data.to_pickle(destination)
        print(f"Written {destination} file with {old_data.shape[0]} records")
        f_time = time.perf_counter()
        elapsed = f_time - s_time
        print(f"time elapsed: {str(elapsed)} seconds")
        print("-" * 75)
        return


if __name__ == "__main__":
    # get_lyrics_for_charting_tracks(chart_type="old")
    get_lyrics_for_charting_tracks(chart_type="new")
