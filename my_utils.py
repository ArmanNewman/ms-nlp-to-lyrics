import json
from typing import Dict, Optional
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import pandas as pd

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
            for idx, hit in enumerate(hits):
                record = {}
                hit_r = hit["result"]
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
        lyrics_divs = soup.find_all(
            "div", class_="Lyrics__Container-sc-1ynbvzw-6 YYrds"
        )
        lyrics_parts = []
        for div in lyrics_divs:
            lyrics_i = div.get_text("\n")
            lyrics_parts.append(lyrics_i)

        lyrics = "\n".join(lyrics_parts)
        return {"url": lyrics_url, "lyrics": lyrics}


if __name__ == "__main__":
    s = HTMLSession()

    # Test get metadata from Genius API
    sample_metadata = get_genius_metadata(s=s, search_term="the weeknd save your tears")
    print(sample_metadata)

    # Retrieve the Lyrics
    lyrics = get_lyrics(s=s, lyrics_url=sample_metadata.url[0])
    print(lyrics)
