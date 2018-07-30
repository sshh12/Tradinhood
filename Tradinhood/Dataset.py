from datetime import datetime
import pandas as pd
import requests

class Dataset:

    def __init__(self, df):
        self.df = df

    @classmethod
    def from_google(self, symbol, interval=60, period='20d', exchange='NASD'):

        res = requests.get(f'https://www.google.com/finance/getprices?i={interval}&p={period}&f=d,o,h,l,c,v&df=cpct&q={symbol}&x={exchange}').text
        lines = res.split('\n')[7:]

        ref_date = None
        records = []
        indexes = []

        for line in lines:

            if not line:
                continue

            date, close, high, low, open, volume = line.split(',')

            if date.startswith('a'):
                date = int(date[1:])
                ref_date = date
            else:
                date = ref_date + interval * int(date)

            timestamp = datetime.fromtimestamp(date).isoformat()

            records.append([close, high, low, open, volume])
            indexes.append((timestamp, symbol))

        df_index = pd.MultiIndex.from_tuples(indexes, names=['date', 'symbol'])
        df = pd.DataFrame.from_records(records, index=df_index, columns=['close', 'high', 'low', 'open', 'volume'])

        return Dataset(df)

    def __or__(self, other):

        assert isinstance(other, Dataset)

        new_df = self.df.append(other.df)

        return Dataset(new_df)
