python get_unique_tracks.py &&
    python get_track_genius_metadata.py >>metadata.log &&
    python get_genius_lyrics.py >>lyrics.log &&
    python glue.py >>glue.log
