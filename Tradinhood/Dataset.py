from dataclasses import dataclass
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
import requests

@dataclass
class OHLCV:
    open: float
    high: float
    low: float
    close: float
    volume: float

class Dataset:

    def __init__(self, data):
        self.data = data

    @classmethod
    def from_google(self, symbol, interval=60, period='20d', exchange='NASD'):

        res = requests.get(f'https://www.google.com/finance/getprices?i={interval}&p={period}&f=d,o,h,l,c,v&df=cpct&q={symbol}&x={exchange}').text
        lines = res.split('\n')[7:]

        ref_date = None
        new_data = defaultdict(dict)

        for line in lines:

            if not line:
                continue

            date, close, high, low, open, volume = line.split(',')

            open = float(open)
            high = float(high)
            low = float(low)
            close = float(close)
            volume = float(volume)

            if date.startswith('a'):
                date = int(date[1:])
                ref_date = date
            else:
                date = ref_date + interval * int(date)

            timestamp = datetime.fromtimestamp(date).isoformat()

            new_data[timestamp][symbol] = OHLCV(open, high, low, close, volume)

        return Dataset(new_data)

    @property
    def dates(self):
        return sorted(self.data.keys())

    def get(self, timestamp, symbol, default=None):
        try:
            return self.data[timestamp][symbol]
        except KeyError:
            return default

    def __or__(self, other):

        assert isinstance(other, Dataset)

        for time in other.data:
            for symbol in other.data[time]:
                self.data[time][symbol] = other.data[time][symbol]

        return self
