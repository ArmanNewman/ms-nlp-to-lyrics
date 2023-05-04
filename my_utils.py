import os
import re
import json
import urllib.parse
from typing import Dict, Optional
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import pandas as pd

rapidApi_key = os.environ["RAPID_API_KEY"]


# 1) API Chart Lyrics is not good enough. Many tracks missing
# 2) API Genius seems to be good
def get_genius_metadata(s: HTMLSession, search_term: str) -> Optional[pd.DataFrame]:
    headers = {
        "Authorization": "Bearer mt6jWadecre1kXN0aQDBKfMKFm-eoJNLA6QTFZ7bMhciKmjPR82q83E0Wkktyy3U"
    }
    search_url = "https://api.genius.com/search?"
    q_params = {"q": search_term}
    res = s.get(search_url, params=q_params, headers=headers)
    if res.status_code == 200:
        res_decoded = res.content.decode("utf-8")
        res_json = json.loads(res_decoded)
        hits = res_json["response"]["hits"]
        if hits:
            search_results = []
            # Spotify, Apple or Genius Patterns
            gen_patt = re.compile("by\WGenius")
            spoti_patt = re.compile("by\WSpotify")
            appl_patt = re.compile("by\WApple")

            # Mix or Remix Patterns
            remix_patt = re.compile(r"\bremix\b", flags=re.IGNORECASE)
            mix_patt = re.compile(r"\bmix\b", flags=re.IGNORECASE)
            for idx, hit in enumerate(hits):
                record = {}
                hit_r = hit["result"]
                hit_full_title = hit_r["full_title"]

                # Regex Patterns for Guards
                search_gen = gen_patt.search(hit_full_title)
                search_spoti = spoti_patt.search(hit_full_title)
                search_appl = appl_patt.search(hit_full_title)

                # Regex Patterns for Remixes Guards
                search_remix = remix_patt.search(hit_full_title)
                search_mix = mix_patt.search(hit_full_title)

                # Guards
                if search_gen or search_spoti or search_appl:
                    continue  # Skip that record (translations or other stuff)
                elif search_remix or search_mix:
                    continue  # Skip remixes
                elif "emulation" in hit_r["url"]:
                    continue
                elif "lyrics" not in hit_r["url"]:
                    continue  # Skip urls not directing to Lyrics
                record["hit_idx"] = idx
                record["search_term"] = search_term
                record["api_path"] = hit_r["api_path"]
                record["artist_names"] = hit_r["artist_names"]
                record["full_title"] = hit_r["full_title"]
                record["header_image_thumbnail_url"] = hit_r[
                    "header_image_thumbnail_url"
                ]
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
                record["song_art_image_thumbnail_url"] = hit_r[
                    "song_art_image_thumbnail_url"
                ]
                record["song_art_image_url"] = hit_r["song_art_image_url"]
                record["title"] = hit_r["title"]
                record["title_with_featured"] = hit_r["title_with_featured"]
                record["url"] = hit_r["url"]

                search_results.append(record)
            return pd.DataFrame(search_results)


def get_lyrics(s: HTMLSession, lyrics_url: str) -> Optional[Dict[str, str]]:
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


def test_lyrics_api(s: HTMLSession, title: str, artist: str):
    search_url = "https://worldwide-songs-and-lyrics.p.rapidapi.com/api/music/search"
    search_term = title + " " + artist
    title_parsed = urllib.parse.quote(search_term)

    search_payload = f"q={title_parsed}&country=US&shelf=song"
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "X-RapidAPI-Key": rapidApi_key,
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


def search_lyrics_on_fallback(s: HTMLSession, query: str):
    # Build the request URL for the Lyrics.ovh API
    fallback_base_url = "https://api.lyrics.ovh/v1"
    search_url = fallback_base_url + "/" + urllib.parse.quote(query)

    # Send the request to the Lyrics.ovh API and parse the response
    fallback_response = s.get(search_url)
    fallback_data = json.loads(fallback_response.text)

    # Check if any songs were found on the fallback API
    if fallback_data["lyrics"] == "":
        print("No lyrics found.")
        return

    # Print the search results from the fallback API
    print("Search results (Fallback):")
    print("- " + query)

    # Ask the user to confirm the song on the fallback API
    fallback_choice = input("Do you want to get the lyrics for this song? (Y/N): ")
    if fallback_choice.lower() == "y":
        print(fallback_data["lyrics"])
        return fallback_data["lyrics"]
    else:
        print("Lyrics not found.")
        return


if __name__ == "__main__":
    s = HTMLSession()
    pd.options.display.max_columns = None
    pd.options.display.max_colwidth = None

    # Test get metadata from Genius API
    # sample_metadata = get_genius_metadata(s=s, search_term="the weeknd save your tears")
    # print(sample_metadata)

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
    test_term = "sunflower by post malone"

    search_res = get_genius_metadata(s=s, search_term=test_term)
    print(search_res)

    # f_res = search_lyrics_on_fallback(s, test_term)
    # print(f_res)

    # 2. Retrieve the Lyrics with song id
    # lyrics = get_lyrics(s=s, lyrics_url=sample_metadata.url[0])

    # url = "https://genius.com/Karol-g-and-shakira-tqg-lyrics"
    # lyrics = get_lyrics(s=s, lyrics_url=url)
    # print(lyrics)

    # print("-" * 15, "Testing New API", "-" * 15)
    # lyrs = test_lyrics_api(
    #     s=s, title="gatita que le gusta el mambo", artist="bellakath"
    # )
    # print(lyrs)
