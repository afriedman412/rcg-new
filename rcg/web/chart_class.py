import pandas as pd
from pandas import DataFrame
from typing import Tuple, Literal
import regex as re
from .. import db_ # TODO: this, better
import datetime as dt
from ..config.config import COLORS, GENDERS # TODO: also this, better

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from io import BytesIO
import base64
import logging # TODO: add logging


class Chart:
    """
    For acquiring and manipulating chart data.
    """
    def __init__(self, date: str=None):
        self.full_chart, self.chart_date = self.load_chart(date)
        return

    def load_chart(self, date: str=None) -> Tuple[DataFrame, str]:
        """
        Loads the latest Rap Caviar chart from the db.
        
        Assumes largest chart_date is latest chart.

        returns:
        full_chart: dataframe
        chart_date: string of latest chart date
        """
        q = """
            SELECT chart.song_name, chart.primary_artist_name, chart_date, artist.artist_name, gender
            FROM chart
            INNER JOIN song ON chart.song_spotify_id=song.song_spotify_id
            LEFT JOIN artist ON song.artist_spotify_id=artist.spotify_id
            """

        if not date:
            q += """
                WHERE chart_date=(SELECT max(chart_date) FROM chart)
                """
                
        else:
            q += f"""
                WHERE chart_date='{date}'
                """

        full_chart = pd.read_sql(q, db_.engine)

        full_chart['gender'] = full_chart['gender'].map({"m": "Male", "f": "Female", "n": "Non-Binary"})
        chart_date = full_chart['chart_date'][0]
        chart_date = dt.datetime.strptime(chart_date, "%Y-%m-%d").strftime("%B %d, %Y")
        return full_chart, chart_date
    
    @property
    def count_data(self) -> DataFrame:
        count_data = pd.DataFrame(
                [
                self.full_chart['gender'].value_counts(),
                self.full_chart['gender'].value_counts(normalize=True).round(3)*100],
                ["Total", "Percentage"]
            )

        return count_data

    def gender_count_data(self, g: Literal["m", "f", "n", "x"]):
        return self.count_data.to_dict().get(g, None)

    def make_plots(self):
        count_data = self.count_data.T
        fig, ax = plt.subplots(1,2, figsize=(8,5))

        sns.barplot(
            x=count_data.index, 
            y=count_data['Total'],
            ax=ax[0],
            palette=[COLORS['Male'], COLORS['Female'],COLORS['Non-Binary']]
        );

        ax[0].set_title(f"Total Artist Credits\n({self.chart_date})")

        sns.barplot(
            x=count_data.index, 
            y=count_data['Percentage'],
            ax=ax[1],
            palette=[COLORS['Male'], COLORS['Female'],COLORS['Non-Binary']]
        );

        ax[1].set_title(f"% of Artist Credits\n({self.chart_date})")

        img=BytesIO()
        fig.savefig(img, format='png')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf8')
        return plot_url

    @property
    def chart_w_features(self) -> DataFrame:
        """
        Adds "Features" column to the full chart.
        """
        features = self.full_chart.query("primary_artist_name != artist_name").groupby("song_name")['artist_name'].apply(lambda a: ", ".join(a))
        main_chart = self.full_chart.query("primary_artist_name == artist_name").set_index("song_name")
        chart_w_features = main_chart.drop(
            ['chart_date', 'artist_name', 'gender'],axis=1).join(features).reset_index().rename(columns={'artist_name':'features'}).fillna("")

        chart_w_features.columns = ['Song', 'Primary Artist', 'Features']
        chart_w_features['Song'] = chart_w_features['Song'].map(self.remove_features_from_title)
        return chart_w_features.to_dict('records')

    def remove_features_from_title(self, t):
        return re.sub(r"\s[\(\[](feat\.|with).+[\)\]]", "", t)

    @property
    def total_chart_dict(self) -> dict:
        """
        Extracts gender data and converts to one dict.
        """
        total_df = self.full_chart['gender'].value_counts().rename_axis('gender').reset_index(name='count') # gender count
        pct_df = self.full_chart['gender'].value_counts(normalize=True).rename_axis('gender').reset_index(name='pct') # gender pct
        pct_df['pct'] = pct_df['pct'].map(lambda c: c*100).round(2) # formatted gender pct
        total_df=total_df.set_index('gender').join(pct_df.set_index("gender")).reset_index() # join counts and pct
        total_chart_dict = total_df.to_dict("records") # convert to dict
        for k in set(GENDERS).difference(set([d['gender'] for d in total_chart_dict])):
            total_chart_dict.append({"gender":k, "count":0, "pct":0}) # add any missing genders
        return total_chart_dict

    @property
    def gender_counts_prep(self) -> DataFrame:
        """
        Formats artist-wise gender counts for "Tally". Done this way for annoying formatting reasons.
        """
        gender_counts = {
            c:self.full_chart.query(
                f"gender=='{c}'")['artist_name'].value_counts().reset_index().rename(
                    columns={"index": f"artist_name_{c[0].lower()}", "artist_name":f"count_{c[0].lower()}"})for c in GENDERS
        }

        gender_counts_full = gender_counts['Male'].join(
            gender_counts['Female']).join(
            gender_counts['Non-Binary']
        )

        gender_counts_full.fillna("", inplace=True)
        
        for c in gender_counts_full.columns:
            if 'count' in c:
                gender_counts_full[c] = gender_counts_full[c].map(lambda c: int(c) if isinstance(c, float) else c)

        return gender_counts_full.fillna("")

    @property
    def gender_counts_keys(self) -> Tuple:
        """
        Formatting things here I can't figure out how to format in Jinja
        """
        return [(f"artist_name_{g}", f"count_{g}") for g in "mfn"]

    @property
    def gender_counts_full(self) -> DataFrame:
        return self.gender_counts_prep.to_dict('records')

    @property
    def gender_indexes(self):
        return list(zip(self.gender_counts_prep.columns[::2], self.gender_counts_prep.columns[1::2]))
    
