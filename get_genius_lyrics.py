from requests_html import HTMLSession
import pandas as pd
import my_utils

s = HTMLSession()

metadata = pd.read_pickle("genius_metadata.pickle")

# Retrieve the Lyrics
lyrics_list = []
print("Total records to query lyrics:", metadata.shape[0])
for i, row in metadata.iterrows():
    print(i, row["url"])
    lyrics_record = my_utils.get_lyrics(s=s, lyrics_url=row["url"])
    if lyrics_record:
        lyrics_list.append(lyrics_record)
    elif not lyrics_record:
        print(i, row["url"], "Does not have lyrics in Genius site")

lyrics_df = pd.DataFrame(lyrics_list)
lyrics_df.to_pickle("lyrics.pickle")

