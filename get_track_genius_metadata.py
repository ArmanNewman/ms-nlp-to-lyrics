import my_utils
from requests_html import HTMLSession
import pandas as pd

s = HTMLSession()

deduped_tracks = pd.read_pickle("deduped_tracks.pickle")

metadata_dfs = []
for df_idx, row in deduped_tracks.iterrows():
    df_i = my_utils.get_genius_metadata(s=s, search_term=row["search_term"])
    metadata_dfs.append(df_i)
metadata = pd.concat(metadata_dfs)

# Select only the first hit
metadata = metadata.loc[metadata.hit_idx == 0]

# Drop cases with duplicate URLs for lyrics
metadata.drop_duplicates(subset="url", keep="first", inplace=True)

# Drop cases where 'lyrics' is not present in the url
metadata = metadata.loc[metadata.url.str.contains("lyrics", regex=False)]

metadata.to_pickle("genius_metadata.pickle")
