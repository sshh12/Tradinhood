from collections import defaultdict
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pandas as pd
import random
import time

from .Dataset import RESOLUTIONS

class BaseTrader:

    ### Base Methods ###

    def __init__(self, symbols):

        assert len(symbols) > 0

        self.log = defaultdict(list)
        self.symbols = symbols

    def _step(self, current_date, *args, **kwargs):

        ## Pre
        self.log['datetime'].append(current_date)
        self.log['start_cash'].append(self.cash)
        self.log['start_portfolio_value'].append(self.portfolio_value)

        for symbol in self.symbols:
            self.log['start_owned_' + symbol].append(self.quantity(symbol))

        ## Execute
        self.loop(current_date, *args, **kwargs)

        ## Post
        self.log['end_cash'].append(self.cash)
        self.log['end_portfolio_value'].append(self.portfolio_value)

        for symbol in self.symbols:
            self.log['end_owned_' + symbol].append(self.quantity(symbol))

    def log_as_dataframe(self):

        df = pd.DataFrame.from_dict(self.log).set_index('datetime')
        df.index = pd.to_datetime(df.index)

        numeric_cols = ['start_cash', 'end_cash', 'start_portfolio_value', 'end_portfolio_value']
        for symbol in self.symbols:
            numeric_cols.append('start_owned_' + symbol)
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

        return df

    def plot(self, columns=['end_portfolio_value', 'end_cash'], ax=None, show=False):
        df = self.log_as_dataframe()
        df[columns].plot(ax=ax)
        if show: plt.show()

    def plot_assets(self, ax=None, symbols=None, show=False):
        if not symbols:
            symbols = self.symbols
        df = self.log_as_dataframe()
        df[['end_owned_' + symbol for symbol in self.symbols]].plot(ax=ax)
        if show: plt.show()

    ### Runner Methods ###

    def start(self, *args, **kwargs):
        pass

    ### Trading Methods ###

    @property
    def cash(self):
        return 0

    @property
    def portfolio_value(self):
        value = self.cash
        for symbol in self.symbols:
            value += self.quantity(symbol) * self.price(symbol)
        return value

    def quantity(self, symbol):
        return 0

    def set_quantity(self, symbol, amt):
        current = self.quantity(symbol)
        if amt > current:
            self.buy(symbol, amt - current)
        elif amt < current:
            self.sell(symbol, current - amt)

    def price(self, symbol):
        return 0

    def buy(self, symbol, amt, **kwargs):
        return False

    def sell(self, symbol, amt, **kwargs):
        return False

    def history(self, symbol, steps):
        return []

    ### Algo Code ###

    def setup(self):
        pass

    def loop(self, current_date):
        pass

class Backtester(BaseTrader):

    def start(self, dataset, cash=10000, start_idx=50):

        assert all(symbol in dataset.symbols for symbol in self.symbols)

        self.dataset = dataset
        self.steps = self.dataset.dates
        self.idx = start_idx
        self.owned = defaultdict(lambda: 0)
        self._cash = cash

        self.setup()

        for i, current_date in enumerate(self.steps):

            if i < start_idx:
                continue

            self.idx = i
            self._step(current_date)

    @property
    def cash(self):
        return self._cash

    def quantity(self, symbol):
        return self.owned[symbol]

    def price(self, symbol):
        cur_quote = self.dataset.get(self.steps[self.idx], symbol)
        return random.uniform(cur_quote.open, cur_quote.close)

    def history(self, symbol, steps):

        assert self.idx > steps

        hist = []
        for date in self.steps[(self.idx - steps):self.idx]:
            hist.append(self.dataset.get(date, symbol))
        return hist

    def buy(self, symbol, amt, **kwargs):

        price_per = self.price(symbol)
        cost = price_per * amt

        if cost <= self.cash:
            self._cash -= cost
            self.owned[symbol] += amt
            return True
        else:
            return False

    def sell(self, symbol, amt, **kwargs):

        price_per = self.price(symbol)

        if amt <= self.quantity(symbol):
            self._cash += price_per * amt
            self.owned[symbol] -= amt
            return True
        else:
            return False

class Robinhood(BaseTrader):

    def start(self, robinhood, resolution='1d', until=None):

        assert resolution in RESOLUTIONS
        assert robinhood.logged_in

        self.rbh = robinhood
        self.resolution = resolution
        self.stop_date = until

        self.setup()

        while True:

            date_start = datetime.now()
            timestamp = date_start.isoformat()

            if self.stop_date and timestamp > self.stop_date:
                break

            self._step(timestamp)

            date_end = date_start + timedelta(seconds=RESOLUTIONS[self.resolution])
            wait_time = (date_end - datetime.now()).total_seconds()

            if wait_time <= 0:
                print('Your algo\'s loop took longer than a timestep!')
            else:
                time.sleep(wait_time)

    @property
    def cash(self):
        return self.rbh.buying_power

    def quantity(self, symbol):
        return self.rbh.quantity(self.rbh[symbol])

    def price(self, symbol):
        return self.rbh[symbol].price

    def history(self, symbol, steps):
        return []

    def buy(self, symbol, amt, wait=True, **kwargs):
        order = self.rbh.buy(self.rbh[symbol], amt, **kwargs)
        if wait:
            self.rbh.wait_for_orders([order], delay=5, timeout=RESOLUTIONS[self.resolution], force=True)
        return order

    def sell(self, symbol, amt, wait=True, **kwargs):
        order = self.rbh.sell(self.rbh[symbol], amt, **kwargs)
        if wait:
            self.rbh.wait_for_orders([order], delay=5, timeout=RESOLUTIONS[self.resolution], force=True)
        return order
