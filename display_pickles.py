import pandas as pd

# lyrics = pd.read_pickle("lyrics.pickle")

lyrics = pd.read_pickle("genius_metadata.pickle")

print("Lyrics Data:")
print(lyrics.info())
print(lyrics.shape)
print(lyrics.head(15))

# for lyric in lyrics.lyrics:
#     if not isinstance(lyric, str):
#         print(type(lyric))
