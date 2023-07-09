import os
import re
from typing import Dict, Optional
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import pandas as pd
from toolz.functoolz import pipe


def split_song(song: str) -> str:
    return song.split(" - ")[0].lower()


def remove_parenthesis(song: str) -> str:
    """Removes parenthesis and its contents"""
    featuring_pattern = re.compile(r"\(.+?\)")
    return " ".join(featuring_pattern.sub("", song).strip().split())


def remove_brackets(song: str) -> str:
    """Removes square brackets and its contents"""
    featuring_pattern = re.compile(r"\[.+?\]")
    return " ".join(featuring_pattern.sub("", song).strip().split())


def simplify_track_title(song: str) -> str:
    """Keeps the first part if a dash is present, removes parenthesis and converts to lower case."""
    return pipe(song, split_song, remove_parenthesis, remove_brackets)


def get_lyrics_from_genius(s: HTMLSession, lyrics_url: str) -> Dict[str, Optional[str]]:
    lyrics_r = s.get(lyrics_url)
    if lyrics_r.status_code == 200:
        lyrics_s = lyrics_r.content.decode("utf-8")
        soup = BeautifulSoup(lyrics_s, "html.parser")

        # CASE 1: There are lyrics
        lyrics_divs = soup.find_all("div", {"data-lyrics-container": "true"})
        # Check if there are div tags containing the lyrics
        if lyrics_divs:
            lyrics_parts = []
            for div in lyrics_divs:
                lyrics_i = div.get_text("\n")
                lyrics_parts.append(lyrics_i)
            lyrics = "\n".join(lyrics_parts)
            return {"url": lyrics_url, "lyrics": lyrics}

        # CASE 2: The song is instrumental
        lyrics_div_message = soup.find_all(
            name="div", attrs={"class": re.compile("^LyricsPlaceholder__Message")}
        )[0].get_text()
        # Check if there are Lyrics Placeholder indicating the song is an instrumental
        if lyrics_div_message == "This song is an instrumental":
            return {"url": lyrics_url, "lyrics": lyrics_div_message}

        # CASE 3: The lyrics are not yet released
        if (
            lyrics_div_message
            == "Lyrics for this song have yet to be released. Please check back once the song has been released."
        ):
            pass

    # Return a default dictionary if nothing before worked
    return {"url": lyrics_url, "lyrics": None}


def parse_genius_metadata(response, s: HTMLSession) -> Optional[pd.DataFrame]:
    if response.status_code != 200:
        return None
    res_json = response.json()
    hits = res_json["response"]["hits"]
    if not hits:
        # Handle the case when hits is empty
        return None
    search_results = []
    # Spotify, Apple or Genius Patterns
    genius_pattern = re.compile(r"by\WGenius")
    spotify_pattern = re.compile(r"by\WSpotify")
    apple_pattern = re.compile(r"by\WApple")

    # Mix or Remix Patterns
    remix_pattern = re.compile(r"\bremix\b", flags=re.IGNORECASE)
    mix_pattern = re.compile(r"\bmix\b", flags=re.IGNORECASE)

    # Check if the original search term contains remix, that is, the track is in fact a remix
    track_is_remix = remix_pattern.search(response.url)
    for idx, hit in enumerate(hits):
        record = {}
        hit_r = hit["result"]
        hit_full_title = hit_r["full_title"]

        # Regex Patterns for Guards
        search_gen = genius_pattern.search(hit_full_title)
        search_spotify = spotify_pattern.search(hit_full_title)
        search_apple = apple_pattern.search(hit_full_title)

        # Regex Patterns for Remixes Guards
        search_remix = remix_pattern.search(hit_full_title)
        search_mix = mix_pattern.search(hit_full_title)

        # Guards
        if search_gen or search_spotify or search_apple:
            continue  # Skip that record (translations or other stuff)
        elif (search_remix or search_mix) and (not track_is_remix):
            continue  # Skip remixes
        elif "emulation" in hit_r["url"]:
            continue
        elif "lyrics" not in hit_r["url"]:
            continue  # Skip urls not directing to Lyrics
        record["hit_idx"] = idx
        # record["search_term"] = search_term
        record["api_path"] = hit_r["api_path"]
        record["artist_names"] = hit_r["artist_names"]
        record["full_title"] = hit_r["full_title"]
        record["header_image_thumbnail_url"] = hit_r["header_image_thumbnail_url"]
        record["header_image_url"] = hit_r["header_image_url"]
        record["id"] = hit_r["id"]
        record["language"] = hit_r.get("language")
        record["lyrics_owner_id"] = hit_r["lyrics_owner_id"]
        record["lyrics_state"] = hit_r["lyrics_state"]
        record["path"] = hit_r["path"]
        record["relationships_index_url"] = hit_r["relationships_index_url"]
        rd_c = hit_r["release_date_components"]
        if rd_c:
            record["release_year"] = rd_c.get("year", None)
            record["release_month"] = rd_c.get("month", None)
            record["release_day"] = rd_c.get("day", None)
        record["release_date_for_display"] = hit_r["release_date_for_display"]
        record["song_art_image_thumbnail_url"] = hit_r["song_art_image_thumbnail_url"]
        record["song_art_image_url"] = hit_r["song_art_image_url"]
        record["title"] = hit_r["title"]
        record["title_with_featured"] = hit_r["title_with_featured"]
        record["url"] = hit_r["url"]

        search_results.append(record)
    if search_results:
        # If there are results, return the first one (most likely correct)
        lyrics_url = search_results[0].get("url")
        lyrics = get_lyrics_from_genius(s=s, lyrics_url=lyrics_url)
        genius_df = pd.DataFrame(search_results[0], index=[0])
        lyrics_raw_text = lyrics.get("lyrics")
        genius_df["lyrics"] = lyrics_raw_text
        return genius_df.replace({"lyrics": {"": None}})
    # Return a default response if Genius cannot find the lyrics url
    return None


def get_lyrics_from_rapidapi(
    s: HTMLSession, search_term: str, rapid_api_key: str
) -> Dict[str, str]:
    search_url = "https://worldwide-songs-and-lyrics.p.rapidapi.com/api/music/search"

    search_payload = f"q={search_term}&country=US&shelf=song"
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "X-RapidAPI-Key": rapid_api_key,
        "X-RapidAPI-Host": "worldwide-songs-and-lyrics.p.rapidapi.com",
    }

    search_response = s.request(
        "POST", search_url, data=search_payload, headers=headers
    )
    if search_response.status_code != 200:
        return {
            "error_case": f"1) Term not found. Status code: {search_response.status_code}"
        }
    search_r = search_response.json()
    data = search_r["results"]["data"]
    if not data:
        return {"error_case": "2) No data for the term passed"}
    song_id = data[0]["id"]

    lyrics_url = "https://worldwide-songs-and-lyrics.p.rapidapi.com/api/music/lyric"

    lyrics_payload = f"id={song_id}&country=US"

    response = s.request("POST", lyrics_url, data=lyrics_payload, headers=headers)
    if response.status_code == 200:
        return {"lyrics": response.json()["results"]["description"]["text"]}
    return {"error_case": f"1) Lyrics not found. Status code: {response.status_code}"}


def get_lyrics(
    s: HTMLSession, search_term: str, song_title: str, api_key: Optional[str] = None
) -> pd.DataFrame:
    headers = {
        "Authorization": "Bearer mt6jWadecre1kXN0aQDBKfMKFm-eoJNLA6QTFZ7bMhciKmjPR82q83E0Wkktyy3U"
    }
    search_url = "https://api.genius.com/search?"
    q_params = {"q": search_term}
    res = s.get(search_url, params=q_params, headers=headers)
    # Define a default response to return when failure
    exception_response = pd.DataFrame(
        {"search_term": [search_term], "requires_callback": [True]}
    )

    def try_rapidapi(s, api_key, search_term, song_title) -> Optional[pd.DataFrame]:
        search_terms = [search_term, song_title]
        for i, st in enumerate(search_terms, start=1):
            rapidapi_resp = get_lyrics_from_rapidapi(
                s=s, search_term=st, rapid_api_key=api_key
            )
            rapidapi_lyrics = rapidapi_resp.get("lyrics")
            if rapidapi_lyrics:
                rapid_data = {
                    "search_term": st,
                    "lyrics_source": f"RapidApi {i}",
                    "lyrics": rapidapi_lyrics,
                }
                return pd.DataFrame([rapid_data])

    # Attempts with Genius
    # First Attempt
    metadata = parse_genius_metadata(res, s=s)
    # If the first attempt worked, add column with the search term
    if metadata is not None:
        first_attempt_lyrics = metadata.lyrics[0]
        # Handle case when Genius found the lyrics but they are not released yet
        if first_attempt_lyrics is None or first_attempt_lyrics == "":
            # Attempts with RapidApi if a key is provided
            if api_key:
                lyr_df = try_rapidapi(s, api_key, search_term, song_title)
                if lyr_df is not None:
                    return lyr_df

            metadata["search_term"] = search_term
            metadata["lyrics_source"] = "Genius 1"
            return metadata

    # Second Attempt
    song_title = simplify_track_title(song_title)
    q_params = {"q": song_title}
    new_res = s.get(search_url, params=q_params, headers=headers)
    metadata = parse_genius_metadata(new_res, s=s)
    # If the second attempt worked, add column with the search term equal to the simplified track
    if metadata is not None:
        metadata["search_term"] = song_title
        metadata["lyrics_source"] = "Genius 2"
        return metadata

    # Attempts with RapidApi if a key is provided
    if api_key:
        lyr_df = try_rapidapi(s, api_key, search_term, song_title)
        if lyr_df is not None:
            return lyr_df

    return exception_response


def test_genius_search(s: HTMLSession, search_term: str):
    headers = {
        "Authorization": "Bearer mt6jWadecre1kXN0aQDBKfMKFm-eoJNLA6QTFZ7bMhciKmjPR82q83E0Wkktyy3U"
    }
    search_url = "https://api.genius.com/search?"
    q_params = {"q": search_term}
    response = s.get(search_url, params=q_params, headers=headers)
    hits = response.json()["response"]["hits"]
    print("#" * 100)
    for i, hit in enumerate(hits):
        print(f"index: {i}")
        result = hit["result"]
        print("lyrics_owner_id:", result["lyrics_owner_id"])
        print("primary_artist_id:", result["primary_artist"]["id"])
        print("primary_artist_name:", result["primary_artist"]["name"])
        print("artist_names:", result["artist_names"])
        print("full_title:", result["full_title"])
        print("lyrics_url:", result["url"])
        print("-" * 50)
    print("#" * 100)
    return response, hits


if __name__ == "__main__":
    rapidApi_key = os.environ["RAPID_API_KEY"]
    s = HTMLSession()
    pd.options.display.max_columns = 150
    pd.options.display.max_colwidth = 9_000

    # Test function remove_parenthesis
    txt_parenthesis = "no me conocen (con duki, rei & tiago pzk) by bandido"
    txt_parenthesis_removed = remove_parenthesis(txt_parenthesis)
    assert txt_parenthesis_removed == "no me conocen by bandido"

    # Test function remove_brackets
    txt_brackets = "entre nosotros [con nicki nicole] by tiago pzk"
    txt_brackets_removed = remove_brackets(txt_brackets)
    assert txt_brackets_removed == "entre nosotros by tiago pzk"

    # Test Genius Pattern
    txt_genius = "Post Malone & Swae Lee - Sunflower (Traducción al Español) by Genius Traducciones al Español"
    genius_pattern = re.compile(r"by\WGenius")
    search_gen = genius_pattern.search(txt_genius)
    assert search_gen is not None

    # Test Genius Search endpoint
    save_your_tears_resp, save_your_tears = test_genius_search(
        s=s, search_term="save your tears"
    )
    sunflower_resp, sunflower = test_genius_search(s=s, search_term="sunflower")
    dy_remix_resp, dy_remix = test_genius_search(
        s=s, search_term="remix by daddy yankee"
    )
    # Test full process with 1 track
    sample_lyrics = get_lyrics(
        s=s, search_term="gato de noche by ñengo flow", song_title="Gato de Noche"
    )
    print(sample_lyrics)
