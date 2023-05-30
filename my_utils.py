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
    featuring_pattern = re.compile("\(.+?\)")
    return featuring_pattern.sub("", song).strip()


def simplify_track_title(song: str) -> str:
    """Keeps the first part if a dash is present, removes parenthesis and converts to lower case."""
    return pipe(song, split_song, remove_parenthesis)


def get_lyrics_from_genius(s: HTMLSession, lyrics_url: str) -> Dict[str, Optional[str]]:
    lyrics_r = s.get(lyrics_url)
    if lyrics_r.status_code == 200:
        lyrics_s = lyrics_r.content.decode("utf-8")
        soup = BeautifulSoup(lyrics_s, "html.parser")
        lyrics_divs = soup.find_all("div", {"data-lyrics-container": "true"})
        lyrics_parts = []
        for div in lyrics_divs:
            lyrics_i = div.get_text("\n")
            lyrics_parts.append(lyrics_i)

        lyrics = "\n".join(lyrics_parts)
        return {"url": lyrics_url, "lyrics": lyrics}
    return {"url": lyrics_url, "lyrics": None}


def parse_genius_metadata(response) -> Optional[pd.DataFrame]:
    if response.status_code != 200:
        return None
    res_json = response.json()
    hits = res_json["response"]["hits"]
    if not hits:
        # Handle the case when hits is empty
        return None
    search_results = []
    # Spotify, Apple or Genius Patterns
    genius_pattern = re.compile("by\WGenius")
    spotify_pattern = re.compile("by\WSpotify")
    apple_pattern = re.compile("by\WApple")

    # Mix or Remix Patterns
    remix_pattern = re.compile(r"\bremix\b", flags=re.IGNORECASE)
    mix_pattern = re.compile(r"\bmix\b", flags=re.IGNORECASE)
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
        elif search_remix or search_mix:
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
        record["language"] = hit_r["language"]
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
        lyrics_url = search_results[0].get("url")
        lyrics = get_lyrics_from_genius(s=s, lyrics_url=lyrics_url)
        genius_df = pd.DataFrame(search_results[0], index=[0])
        genius_df["lyrics"] = lyrics.get("lyrics")
        return genius_df
    # Return a default response if Genius cannot find the lyrics url
    return None


# 1) API Chart Lyrics is not good enough. Many tracks missing
# 2) API Genius seems to be good
# def get_genius_metadata(s: HTMLSession, search_term: str) -> pd.DataFrame:
#     headers = {
#         "Authorization": "Bearer mt6jWadecre1kXN0aQDBKfMKFm-eoJNLA6QTFZ7bMhciKmjPR82q83E0Wkktyy3U"
#     }
#     search_url = "https://api.genius.com/search?"
#     q_params = {"q": search_term}
#     res = s.get(search_url, params=q_params, headers=headers)
#     # Define a default response to return when failure
#     exception_response = pd.DataFrame(
#         {"search_term": [search_term], "requires_callback": [True]}
#     )
#     if res.status_code != 200:
#         return exception_response
#     res_json = res.json()
#     hits = res_json["response"]["hits"]
#     if not hits:
#         # Handle the case when hits is empty
#         return exception_response
#     search_results = []
#     # Spotify, Apple or Genius Patterns
#     genius_pattern = re.compile("by\WGenius")
#     spotify_pattern = re.compile("by\WSpotify")
#     apple_pattern = re.compile("by\WApple")

#     # Mix or Remix Patterns
#     remix_pattern = re.compile(r"\bremix\b", flags=re.IGNORECASE)
#     mix_pattern = re.compile(r"\bmix\b", flags=re.IGNORECASE)
#     for idx, hit in enumerate(hits):
#         record = {}
#         hit_r = hit["result"]
#         hit_full_title = hit_r["full_title"]

#         # Regex Patterns for Guards
#         search_gen = genius_pattern.search(hit_full_title)
#         search_spotify = spotify_pattern.search(hit_full_title)
#         search_apple = apple_pattern.search(hit_full_title)

#         # Regex Patterns for Remixes Guards
#         search_remix = remix_pattern.search(hit_full_title)
#         search_mix = mix_pattern.search(hit_full_title)

#         # Guards
#         if search_gen or search_spotify or search_apple:
#             continue  # Skip that record (translations or other stuff)
#         elif search_remix or search_mix:
#             continue  # Skip remixes
#         elif "emulation" in hit_r["url"]:
#             continue
#         elif "lyrics" not in hit_r["url"]:
#             continue  # Skip urls not directing to Lyrics
#         record["hit_idx"] = idx
#         record["search_term"] = search_term
#         record["api_path"] = hit_r["api_path"]
#         record["artist_names"] = hit_r["artist_names"]
#         record["full_title"] = hit_r["full_title"]
#         record["header_image_thumbnail_url"] = hit_r["header_image_thumbnail_url"]
#         record["header_image_url"] = hit_r["header_image_url"]
#         record["id"] = hit_r["id"]
#         record["language"] = hit_r["language"]
#         record["lyrics_owner_id"] = hit_r["lyrics_owner_id"]
#         record["lyrics_state"] = hit_r["lyrics_state"]
#         record["path"] = hit_r["path"]
#         record["relationships_index_url"] = hit_r["relationships_index_url"]
#         rd_c = hit_r["release_date_components"]
#         if rd_c:
#             record["release_year"] = rd_c.get("year", None)
#             record["release_month"] = rd_c.get("month", None)
#             record["release_day"] = rd_c.get("day", None)
#         record["release_date_for_display"] = hit_r["release_date_for_display"]
#         record["song_art_image_thumbnail_url"] = hit_r["song_art_image_thumbnail_url"]
#         record["song_art_image_url"] = hit_r["song_art_image_url"]
#         record["title"] = hit_r["title"]
#         record["title_with_featured"] = hit_r["title_with_featured"]
#         record["url"] = hit_r["url"]

#         search_results.append(record)
#     if search_results:
#         lyrics_url = search_results[0].get("url")
#         lyrics = get_lyrics_from_genius(s=s, lyrics_url=lyrics_url)
#         genius_df = pd.DataFrame(search_results[0], index=[0])
#         genius_df["lyrics"] = lyrics.get("lyrics")
#         return genius_df
#     # Return a default response if Genius cannot find the lyrics url
#     return exception_response


def get_genius_metadata(
    s: HTMLSession, search_term: str, song_title: str
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

    # First Attempt
    metadata = parse_genius_metadata(res)
    # If the first attempt worked, add column with the search term
    if metadata is not None:
        metadata["search_term"] = search_term
        metadata["lyrics_source"] = "Genius 1"
        return metadata

    # Second Attempt
    song_title = simplify_track_title(song_title)
    q_params = {"q": song_title}
    new_res = s.get(search_url, params=q_params, headers=headers)
    metadata = parse_genius_metadata(new_res)
    # If the second attempt worked, add column with the search term equal to the simplified track
    if metadata is not None:
        metadata["search_term"] = song_title
        metadata["lyrics_source"] = "Genius 2"
        return metadata
    return exception_response


def search_lyrics_on_fallback(s: HTMLSession, query: str):
    return


def get_lyrics_from_rapidapi(s: HTMLSession, search_term: str, rapid_api_key: str):
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
        return None
    search_r = search_response.json()
    data = search_r["results"]["data"]
    if not data:
        return None
    song_id = data[0]["id"]

    lyrics_url = "https://worldwide-songs-and-lyrics.p.rapidapi.com/api/music/lyric"

    lyrics_payload = f"id={song_id}&country=US"

    response = s.request("POST", lyrics_url, data=lyrics_payload, headers=headers)
    if response.status_code == 200:
        return response.json()["results"]["description"]["text"]


# Expected Output: ['uri', 'artist_names', 'track_name', 'search_term', 'url', 'lyrics']

if __name__ == "__main__":
    rapidApi_key = os.environ["RAPID_API_KEY"]
    s = HTMLSession()
    pd.options.display.max_columns = 150
    pd.options.display.max_colwidth = 9_000

    # TESTS
    # Test 1: Get metadata from Genius API
    # Test 2: Get lyrics from Genius by passing the search_term
    # Test 3: Get lyrics from Genius by passing only song_title if the prior method did not work
    # Test 4: Get lyrics from RapidApi if the 2 prior methods did not work

    # Test 1: Get metadata from Genius API
    # print("Test 1:")
    # t1 = get_genius_metadata(
    #     s=s, search_term="the weeknd save your tears", song_title="save your tears"
    # )
    # print(t1)

    # Test 2: Get lyrics from Genius by passing the search_term
    # print("Test 2:")
    # t2 = get_lyrics_from_genius(s=s, lyrics_url=t1.iloc[0].url)
    # print(t2)

    # Test 3: Get lyrics from Genius by passing only song_title if the prior method did not work
    test_spotify_uris = [
        "spotify:track:4KDgQ8Qd0UWK3KkYZPwNtP",
        "spotify:track:5xwP3VbM3eBKOeFF3fwn6Z",
        "spotify:track:2r69ZhXm40bzjGIPdRvaqk",
        "spotify:track:6CRRlfXDdhsL6vih3J5xco",
        "spotify:track:4xqrdfXkTW4T0RauPLv3WA",
        "spotify:track:3yE8qL9HNfyzAbpqoMnUr8",
        "spotify:track:3MdhvQ8BprBhd4lYlgtPt2",
        "spotify:track:1GBaQ3nnwxO3WVDUzKZ4kX",
        "spotify:track:1wtOxkiel43cVs0Yux5Q4h",
        "spotify:track:6wtZPYBIXUvCpXwVjMCJBf",
        "spotify:track:7KokYm8cMIXCsGVmUvKtqf",
        "spotify:track:4D7BCuvgdJlYvlX5WlN54t",
        "spotify:track:7FmYn9e7KHMXcxqGSj9LjH",
        "spotify:track:5zwwW9Oq7ubSxoCGyW1nbY",
        "spotify:track:6HOOykUGBMv3LFsR9gObw5",
        "spotify:track:63BZhuQ6OZQmxy2RERMHko",
        "spotify:track:0skYUMpS0AcbpjcGsAbRGj",
        "spotify:track:4irQHeQLap1F8Roqj3xJXW",
        "spotify:track:1vmRfKejQWsWnE3arhhEit",
        "spotify:track:3IxbwKm0uWtoHJQ04K1YbA",
        "spotify:track:61vEls8FiPl53hu6947W27",
        "spotify:track:2OmVUVVx3pWjNWHxgbliCe",
        "spotify:track:6746mUlyXUbMeWzBqMTYEi",
        "spotify:track:05bfbizlM5AX6Mf1RRyMho",
        "spotify:track:6ioupaJ387IxHQC9RSHMar",
        "spotify:track:3fzC9A2azykZmtSHuXt0kg",
        "spotify:track:51Zw1cKDgkad0CXv23HCMU",
        "spotify:track:4TGwERXRlyQtBdggYTHo6j",
        "spotify:track:5QxL7Nv8J5gPqD6H0bKmAN",
        "spotify:track:6OpRwk4F7sD8lcNwQdekpO",
        "spotify:track:65MqlYPOWReasKWcuCaOCW",
        "spotify:track:4bV5sf2B4hWBBd5HQ8S7KB",
        "spotify:track:30eHHpkjMNqb2F0V8nXjbJ",
        "spotify:track:5bP1RCdGcUxkwASwKAbPHa",
        "spotify:track:5enxwA8aAbwZbf5qCHORXi",
        "spotify:track:3mV5TTtHnXUeOzRkyFKsVl",
        "spotify:track:7COGuXyTr12KvdaYXMqheC",
        "spotify:track:0pqnGHJpmpxLKifKRmU6WP",
        "spotify:track:4A9u8OrzFYbxdjiydkNdUi",
        "spotify:track:22Sh5dlwbERqJAq1fZk5b2",
        "spotify:track:6EHrppRT1Uj4cyShAujxFu",
        "spotify:track:59nnGpAU3AiL2tD0o2It11",
        "spotify:track:4TgxFMOn5yoESW6zCidCXL",
        "spotify:track:4YqCBC4FwzGXuhixt5cgmm",
        "spotify:track:4MWb6mltydQn84NrTm7Gpl",
        "spotify:track:3f0pjEFyDTp9gMvBQ3XjFz",
        "spotify:track:4jAIqgrPjKLTY9Gbez25Qb",
        "spotify:track:5aJEh9Oqdz7PRLKTpH25pB",
        "spotify:track:2plLJpUcYPFrl1sW2pMG63",
        "spotify:track:63W11KVHDOpSlh3XMQ7qMg",
        "spotify:track:4pj77Vx66vvbodiwLt1wMH",
        "spotify:track:2yGNkkwU2iT0doFxkxhcXH",
        "spotify:track:1PZ3QsCFec05Ls3PwOqKXZ",
    ]
    print("Test 3:")
    df = pd.read_pickle("deduped_tracks.pickle")
    df = df.loc[df.uri.isin(test_spotify_uris)]
    if df.empty:
        exit()

    final_results = []
    for idx, row in df.iterrows():
        print(idx)
        print(row)
        print(row["search_term"])
        print(row["track_name"])

        simplified_track = simplify_track_title(row["track_name"])
        print(simplified_track)

        t1 = get_genius_metadata(
            s=s, search_term=row["search_term"], song_title=simplified_track
        )
        print(t1)
        final_results.append(t1)
    final_df = pd.concat(final_results)
    exit()

    # 1. Search for lyrics
    # 1.1 Search term pattern: artist1, artist2, ... title
    # test_term = "post malone, swae lee sunflower - spider-man: into the spider-verse"

    # 1.2 Search term pattern: title by artist1, artist2, ...
    # test_term = "sunflower - spider-man: into the spider-verse by post malone, swae lee"

    # 1.3 Search term pattern: simplified title by artist1, artist2, ...
    # This works out
    # test_term = "sunflower by post malone, swae lee"

    # 1.4 Search term pattern: artist1 simplified_title
    # test_term = "post malone sunflower"

    # 1.5 Search term pattern: simplified_title by artist1
    # test_term = "sunflower by post malone"
    # test_term = "tra tra tra by ghetto kids"
    # test_term = "no es por acá by carin leon"
    # test_term = "lo siento bb:/ by tainy"
    # test_term = "911 by fuerza regida"
    # test_term = "ojos marrones by lasso"
    test_term = "dame un beso y dime adios by carin leon"
    test_term = "dame un beso y dime adios"

    search_res = get_genius_metadata(s=s, search_term=test_term)
    print(search_res)

    query_rapidapi = input("Query Rapid API Worldwide songs and lyrics? [y/n]:\n")
    while True:
        if query_rapidapi == "n":
            exit()
        elif query_rapidapi == "y":
            callback_response = get_lyrics_from_rapidapi(s, test_term, rapidApi_key)
            print(callback_response)
        else:
            query_rapidapi = input(
                "Enter a valid key. That is, y for yes, n for no: [y/n]:\n"
            )

    # f_res = search_lyrics_on_fallback(s, test_term)
    # print(f_res)

    # 2. Retrieve the Lyrics with song id
    # lyrics = get_lyrics_from_genius(s=s, lyrics_url=sample_metadata.url[0])

    # url = "https://genius.com/Karol-g-and-shakira-tqg-lyrics"
    # lyrics = get_lyrics_from_genius(s=s, lyrics_url=url)
    # print(lyrics)

    # print("-" * 15, "Testing New API", "-" * 15)
