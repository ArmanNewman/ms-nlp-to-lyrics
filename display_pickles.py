import os
import pandas as pd

files = os.listdir()
pickle_files = [f for f in files if f.endswith("pickle")]
for pickle in pickle_files:
    print(pickle)
    data = pd.read_pickle(pickle)

    print(f"{pickle} Data:")
    print(data.info())
    print(data.shape)
    print(data.head(15))

    print("-" * 75, "\n")

# for lyric in lyrics.lyrics:
#     if not isinstance(lyric, str):
#         print(type(lyric))
