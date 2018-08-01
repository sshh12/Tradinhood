from dataclasses import dataclass
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
import requests
import pickle

RESOLUTIONS = {
    '1m': 60,
    '5m': 60*5,
    '1h': 60*60,
    '1d': 60*60*24
}

class DatasetException(Exception):
    pass

@dataclass
class OHLCV:
    open: float
    high: float
    low: float
    close: float
    volume: float

class Dataset:

    def __init__(self, data, resolution, symbols):
        self.data = data
        self.resolution = resolution
        self.symbols = symbols

    @classmethod
    def from_google(self, symbol, resolution='1d', period='20d', exchange='NASD'):

        interval = RESOLUTIONS[resolution]

        url = f'https://www.google.com/finance/getprices?i={interval}&p={period}&f=d,o,h,l,c,v&df=cpct&q={symbol}&x={exchange}'
        res = requests.get(url).text
        lines = res.split('\n')[7:]

        ref_date = None
        new_data = defaultdict(dict)

        for line in lines:

            if not line or '=' in line:
                continue

            date, close, high, low, open_, volume = line.split(',')

            open_ = float(open_)
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

            new_data[timestamp][symbol] = OHLCV(open_, high, low, close, volume)

        if len(new_data) == 0:
            raise DatasetException('No data')

        return Dataset(new_data, resolution, [symbol])

    @classmethod
    def from_cryptocompare(self, symbol, resolution='1d', to_symbol='USD', limit=3000, last_unix_time=None):

        endpoints = {
            '1d': 'histoday',
            '1h': 'histohour',
            '1m': 'histominute'
        }

        url = f'https://min-api.cryptocompare.com/data/{endpoints[resolution]}?fsym={symbol}&tsym={to_symbol}&limit={limit}'
        if last_unix_time:
            url += f'&{last_unix_time}'
        res = requests.get(url).json()

        new_data = defaultdict(dict)

        for data in res['Data']:

            open_ = data['open']
            high = data['high']
            low = data['low']
            close = data['close']
            volume = data['volumefrom']
            timestamp = datetime.fromtimestamp(data['time']).isoformat()

            new_data[timestamp][symbol] = OHLCV(open_, high, low, close, volume)

        if len(new_data) == 0:
            raise DatasetException('No data')

        return Dataset(new_data, resolution, [symbol])


    @classmethod
    def from_file(self, filename):
        try:
            with open(filename, 'rb') as f:
                dataset = pickle.load(f)
            return Dataset(dataset.data, dataset.resolution, dataset.symbols)
        except:
            raise DatasetException('Could not load file ' + filename)

    @property
    def dates(self):
        return sorted(self.data.keys())

    def get(self, timestamp, symbol, default=None):
        try:
            return self.data[timestamp][symbol]
        except KeyError:
            return default

    def save(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    def __repr__(self):
        dates = self.dates
        start, end = dates[0], dates[-1]
        return f'<Dataset |{",".join(self.symbols)}| (@{self.resolution}) [{start} -> {end}]>'

    def __or__(self, other):

        assert isinstance(other, Dataset)
        assert self.resolution == other.resolution

        for time in other.data:
            for symbol in other.data[time]:
                self.data[time][symbol] = other.data[time][symbol]

        self.symbols.extend(other.symbols)

        return self
