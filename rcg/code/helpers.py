from datetime import datetime as dt
import pandas as pd
from pandas import DataFrame
from typing import Tuple

def parse_track(t):
    song_name, song_spotify_id, artists = (t)
    primary_artist_name, primary_artist_spotify_id = (artists[0])
    return song_name, song_spotify_id, artists, primary_artist_name, primary_artist_spotify_id

def parse_genders(l, w):
    try:
        return next(iter({l,w}.intersection('mf')))
    except StopIteration:
        if l == 'n' or w == 'n':
            return 'n'
        else:
            return 'x'

def get_date():
    day = dt.now()
    return day.strftime("%Y-%m-%d")

def load_rap_caviar(sp):
    rc = sp.playlist('spotify:user:spotify:playlist:37i9dQZF1DX0XUsuxWHRQd')
    all_tracks = [
        (p['track']['name'], p['track']['id'], 
        [(a['name'], a['id']) for a in p['track']['artists']]) for p in rc['tracks']['items']
        ]
    return all_tracks

def load_chart(db, chart_date: str=None) -> Tuple[DataFrame, str]:
    """
    Loads the latest Rap Caviar chart from the db.
    TODO: should be able to do this live as well!!
    
    Assumes largest chart_date is latest chart if no chart_date provided.
    """
    q = """
        SELECT chart.song_name, chart.primary_artist_name, chart_date, artist.artist_name, gender
        FROM chart
        INNER JOIN song ON chart.song_spotify_id=song.song_spotify_id
        LEFT JOIN artist ON song.artist_spotify_id=artist.spotify_id
        """

    if not chart_date:
        q += """
            WHERE chart_date=(SELECT max(chart_date) FROM chart)
            """
            
    else:
        q += f"""
            WHERE chart_date='{chart_date}'
            """

    full_chart = pd.read_sql(q, db.engine)

    full_chart['gender'] = full_chart['gender'].map({"m": "Male", "f": "Female", "n": "Non-Binary"})
    if not chart_date:
        chart_date = full_chart['chart_date'][0]
    chart_date = dt.strptime(chart_date, "%Y-%m-%d").strftime("%B %d, %Y")
    return full_chart, chart_date