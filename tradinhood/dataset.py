from collections import defaultdict
from dataclasses import dataclass
import matplotlib.pyplot as plt
from datetime import datetime
from decimal import Decimal
import pandas as pd
import requests
import pickle


RESOLUTIONS = { # The possible dataset resolutions (e.i. every min, every day, etc)
    '1m': 60,
    '5m': 60 * 5,
    '1h': 60 * 60,
    '1d': 60 * 60 * 24
}


class DatasetException(Exception):
    """Exception thrown by a dataset method"""
    pass


@dataclass
class OHLCV:
    """OHLCV

    Basic class for storing price data at a given timestep.

    Attributes:
        open: (float)
        high: (float)
        low: (float)
        close: (float)
        volume: (float)
    """
    open: float
    high: float
    low: float
    close: float
    volume: float


class Dataset:
    """Dataset object

    Attributes:
        data: (dict) The internal object data
            stored as `data[timestep][symbol] = OHLCV()`
        resolution: (str) The resolution of the dataset
            which must be a key of `RESOLUTIONS`
        symbols: (list: str) The symbols included in the dataset
    """

    def __init__(self, data, resolution, symbols):
        """Creates the dataset with predefined params

        This is meant to be called only from the internal `from_...()` class methods
        """
        self.data = data
        self.resolution = resolution
        self.symbols = symbols

    @classmethod
    def from_google(self, symbol, resolution='1d', period='20d', exchange='NASD'):
        """Fetch data from google

        Args:
            symbol: (str) Stock to Fetch
            resolution: (str) The required resolution
                which must be a key of `RESOLUTIONS`
            period: (str) The amount of time to fetch, note:
                google will automatically limit this
            exchange: (str) The stock exchange

        Returns:
            (Dataset) with prescribed params and data
        """
        interval = RESOLUTIONS[resolution]

        url = f'https://www.google.com/finance/getprices?i={interval}&p={period}&f=d,o,h,l,c,v&df=cpct&q={symbol}&x={exchange}'
        res = requests.get(url).text
        lines = res.split('\n')[7:]

        ref_date = None # Use a reference date to keep track of how google API gives time
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
                date = ref_date + interval * int(date) # b/c date can just be an int if intervals since ref_date

            timestamp = datetime.fromtimestamp(date).isoformat()

            new_data[timestamp][symbol] = OHLCV(open_, high, low, close, volume)

        if len(new_data) == 0:
            raise DatasetException('No data')

        return Dataset(new_data, resolution, [symbol])

    @classmethod
    def from_iextrading_charts(self, symbols, period='1d', resolution='1d'):
        """Fetch data from iextrading

        Args:
            symbol: (str or list: str) stock(s) to Fetch
            resolution: (str) The required resolution
                which must be a key of `RESOLUTIONS`
            period: (str) The amount of time to fetch

        Returns:
            (Dataset) with prescribed params and data
        """
        if isinstance(symbols, str): # AMZN -> ['AMZN']
            symbols = [symbols]

        if period != '1d': # if request spans more than a day, force 1d resolution
            assert resolution == '1d'
            chartInterval = 1
        else:
            assert resolution in ['1m', '5m', '1h'] # else if 1d, force min or hour resolution
            chartInterval = RESOLUTIONS[resolution] // 60 # interval is based on mins between datapoint

        symbol_str = ','.join(symbols)
        url = f'https://api.iextrading.com/1.0/stock/market/batch?symbols={symbol_str}&types=chart&range={period}&chartInterval={chartInterval}'
        res = requests.get(url).json()

        new_data = defaultdict(dict)

        for symbol in symbols:

            for data in res[symbol]['chart']:

                open_ = data['open']
                high = data['high']
                low = data['low']
                close = data['close']
                volume = data['volume']

                if resolution in ['1m', '5m', '1h']:
                    date = datetime.strptime(data['date'] + data['minute'], '%Y%m%d%H:%M')
                else:
                    date = datetime.strptime(data['date'], '%Y-%m-%d')

                timestamp = date.isoformat()

                new_data[timestamp][symbol] = OHLCV(open_, high, low, close, volume)

        return Dataset(new_data, resolution, symbols)

    @classmethod
    def from_cryptocompare(self, symbol, resolution='1d', to_symbol='USD', limit=3000, last_unix_time=None):
        """Fetch data from cryptocompare

        Args:
            symbol: (str) Stock to Fetch
            resolution: (str) The required resolution
                which must be a key of `RESOLUTIONS`
            to_symbol: (str) The unit to convert symbol data to,
                this can be a currency or crypto
            limit: (int) limit the num of datapoints returned
            last_unix_time: (int) Specify the last timestep of the query

        Returns:
            (Dataset) with prescribed params and data
        """
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
        """Load from file

        Args:
            filename: (str) The .pkl filename

        Returns:
            (Dataset) from the values in the file
        """
        try:
            with open(filename, 'rb') as f:
                dataset = pickle.load(f)
            return Dataset(dataset.data, dataset.resolution, dataset.symbols) # Cloning params into new dataset for compatibility
        except Exception:
            raise DatasetException('Could not load file ' + filename)

    def save(self, filename):
        """Save dataset

        Args:
            filename: (str) where to save the dataset
        """
        with open(filename, 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    @property
    def dates(self):
        """The dates (in order) that this dataset contains as list: str"""
        return sorted(self.data.keys())

    def get(self, timestamp, symbol, default=None):
        """Get datapoint

        Args:
            timestamp: (str) a timestamp
            symbol: (str) the symbol of interest
            default: A value if not found
        """
        try:
            return self.data[timestamp][symbol]
        except KeyError:
            return default

    def as_dataframe(self, symbols=None):
        """Convert to dataframe

        Args:
            symbols: (list: str) Symbols to include,
                will default to all in dataset

        Returns:
            (Dataframe) with data from dataset
        """
        if not symbols:
            symbols = self.symbols

        data = defaultdict(list)
        data['datetime'] = self.dates

        for symbol in symbols:

            init_close = self.data[data['datetime'][0]][symbol].close # first close price
            prev_close = init_close # previous price

            for timestamp in data['datetime']:
                price_data = self.data[timestamp][symbol]
                data['open_' + symbol].append(price_data.open)
                data['high_' + symbol].append(price_data.high)
                data['low_' + symbol].append(price_data.low)
                data['close_' + symbol].append(price_data.close)
                data['relclose_' + symbol].append(price_data.close / init_close)
                data['relprevclose_' + symbol].append(price_data.close / prev_close)
                data['volume_' + symbol].append(price_data.volume)
                prev_close = price_data.close

        df = pd.DataFrame.from_dict(data).set_index('datetime')
        df.index = pd.to_datetime(df.index)

        return df

    def plot(self, columns=['close'], symbols=None, ax=None, show=False):
        """Plot

        Args:
            columns: (list: str) Columns to plot,
                [open, high, low, close, relclose, relprevclose, volume]
            symbols: (list: str) Symbols to include,
                defaults to all in dataset
            ax: (Axes) Where to plot, defaults to pandas default
            show: (bool) Whether to run plt.show()
        """
        if not symbols:
            symbols = self.symbols

        filter_ = [col + '_' + symbol for col in columns for symbol in symbols] # every column with every symbol

        df = self.as_dataframe(symbols)[filter_].plot(ax=ax, title=str(self)) # dataset -> dataframe -> filter cols -> plot

        if show:
            plt.show()

    def __len__(self):
        """The num of timesteps in the dataset"""
        return len(self.data)

    def __repr__(self):
        """Provides overview of what dataset contains"""
        dates = self.dates
        start, end = dates[0], dates[-1]
        return f'<Dataset |{",".join(self.symbols)}| (@{self.resolution}) [{start} -> {end}]>'

    def __ior__(self, other):
        """Use |= to combine datasets"""
        assert isinstance(other, Dataset)
        assert self.resolution == other.resolution # ensure datasets have the same resolution before trying to join them

        for time in other.data:
            for symbol in other.data[time]:
                self.data[time][symbol] = other.data[time][symbol]

        self.symbols.extend(other.symbols)
        self.symbols = list(set(self.symbols)) # ensure unique

        return self
