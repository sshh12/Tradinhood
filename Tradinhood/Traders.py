from collections import defaultdict
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pandas as pd
import random
import time

from .dataset import RESOLUTIONS


class BaseTrader:
    """The abstract trader

    Attributes:
        log: (dict) a log containing time, cash, and assets
        symbols: (list: str) the symbols tracked
    """
    ### Base Methods ###

    def __init__(self, symbols):
        """Create trader

        Only symbols required, the rest of init is done with .start(...)
        """
        assert len(symbols) > 0 # you have to be trading something...

        self.log = defaultdict(list)
        self.symbols = symbols

    def _step(self, current_date, *args, **kwargs):
        """Run algo one timestep

        This is an internal method used by classes which implement BaseTraderself.
        Do not call with algorithm.
        """
        ## Pre
        self.log['datetime'].append(current_date)
        self.log['start_cash'].append(self.cash)
        self.log['start_portfolio_value'].append(self.portfolio_value)

        for symbol in self.symbols:
            self.log['start_owned_' + symbol].append(self.quantity(symbol))
            self.log['start_price_' + symbol].append(self.price(symbol))

        ## Execute
        self.loop(current_date, *args, **kwargs)

        ## Post
        self.log['end_cash'].append(self.cash)
        self.log['end_portfolio_value'].append(self.portfolio_value)

        for symbol in self.symbols:
            self.log['end_owned_' + symbol].append(self.quantity(symbol))
            self.log['end_price_' + symbol].append(self.price(symbol))

    def log_as_dataframe(self):
        """Convert log to a pandas DataFrame

        Returns:
            (DataFrame)
        """
        df = pd.DataFrame.from_dict(self.log).set_index('datetime')
        df.index = pd.to_datetime(df.index)

        numeric_cols = ['start_cash', 'end_cash', 'start_portfolio_value', 'end_portfolio_value']
        for symbol in self.symbols:
            numeric_cols.append('start_owned_' + symbol)
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

        return df

    def plot(self, columns=['end_portfolio_value', 'end_cash'], ax=None, show=False):
        """Plot money

        Args:
            columns: (list: str) the columns to plot, use .log to find columns
            ax: (Axis) where to plot, defaults to pandas
            show: (bool) display the plot
        """
        df = self.log_as_dataframe()
        df[columns].plot(ax=ax)
        if show:
            plt.show()

    def plot_assets(self, symbols=None, ax=None, show=False):
        """Plot assets

        Args:
            symbols: (list: str) the symbols to include, defaults to all
            ax: (Axis) where to plot, defaults to pandas
            show: (bool) display the plot
        """
        if not symbols:
            symbols = self.symbols
        df = self.log_as_dataframe()
        df[['end_owned_' + symbol for symbol in self.symbols]].plot(ax=ax)
        if show:
            plt.show()

    ### Runner Methods ###

    def start(self, *args, **kwargs):
        """Start.

        Universal start method implemented by Traders
        """
        pass

    ### Trading Methods ###

    @property
    def cash(self):
        """Cash/Buying power"""
        return 0

    @property
    def portfolio_value(self):
        """Portfolio value (cash + stocks + currencies)"""
        value = self.cash
        for symbol in self.symbols:
            value += self.quantity(symbol) * self.price(symbol)
        return value

    def quantity(self, symbol):
        """The owned quantity of symbol"""
        return 0

    def set_quantity(self, symbol, amt):
        """Will buy or sell to set quantity of symbol"""
        current = self.quantity(symbol)
        if amt > current:
            self.buy(symbol, amt - current)
        elif amt < current:
            self.sell(symbol, current - amt)

    def price(self, symbol):
        """Find price of symbol"""
        return 0

    def buy(self, symbol, amt, **kwargs):
        """Buy symbol"""
        return False

    def sell(self, symbol, amt, **kwargs):
        """Sell symbol"""
        return False

    def history(self, symbol, steps):
        """Get history of symbol over steps * resolution"""
        return []

    ### Algo Code ###

    def setup(self):
        """Will run before trading.

        Override with algorithm but do not call (handled by .start(...))
        """
        pass

    def loop(self, current_date):
        """Will run at each timestep

        Override with algorithm but do not call (handled by .start(...))
        """
        pass


class Backtester(BaseTrader):
    """A backtester

    A trader which uses predetermined data from testing an algo.

    Attributes:
        dataset: (Dataset) the dataset used
        steps: (list: str) the timestamps covered by the dataset
    """

    def start(self, dataset, cash=10000, start_idx=50):
        """Start the backtesting

        Args:
            dataset: (Dataset) the dataset to use
            cash: (int) starting cash amt
            start_idx: (int) the timestep in the dataset to start, used to ensure
            .history() with have data to return
        """
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
        """Randomly determines price based on dataset"""
        cur_quote = self.dataset.get(self.steps[self.idx], symbol)
        return random.uniform(cur_quote.open, cur_quote.close)

    def history(self, symbol, steps):

        assert self.idx > steps

        hist = []
        for date in self.steps[(self.idx - steps):self.idx]:
            hist.append(self.dataset.get(date, symbol))
        return hist

    def buy(self, symbol, amt, **kwargs):
        """Simulates a buy"""
        price_per = self.price(symbol)
        cost = price_per * amt

        if cost <= self.cash:
            self._cash -= cost
            self.owned[symbol] += amt
            return True
        else:
            return False

    def sell(self, symbol, amt, **kwargs):
        """Simulates a sell"""
        price_per = self.price(symbol)

        if amt <= self.quantity(symbol):
            self._cash += price_per * amt
            self.owned[symbol] -= amt
            return True
        else:
            return False


class Robinhood(BaseTrader):
    """A Robinhood trader

    A trader which uses Robinhood to execute the trades (IRL)

    Attributes:
        rbh: (Robinhood*) a robinhood client
        resolution: (str) the trade resolution/frequency
    """

    def start(self, robinhood, resolution='1d', until=None):
        """Starts live trading

        Args:
            robinhood: (Robinhood*) a robinhood client, that already has logged in
            resolution: (str) the resolution/freq to trade at
            until: (str) a timestamp at which to stop trading, defaults to forever
        """
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
    def portfolio_value(self):
        """Calc portfolio value based on robinhood assets"""
        value = self.cash
        for asset, amt in self.rbh.get_assets():
            if amt > 0:
                value += amt * asset.price
        return value

    @property
    def cash(self):
        """Robinhood buying power"""
        return self.rbh.buying_power

    def quantity(self, symbol):
        return self.rbh.quantity(self.rbh[symbol])

    def price(self, symbol):
        """The price according to the Robinhood API"""
        return self.rbh[symbol].price

    def history(self, symbol, steps):
        return [] # TODO

    def buy(self, symbol, amt, wait=True, **kwargs):
        """Buy stock/currency

        Args:
            symbol: (str) what to buy
            amt: (int) amt to buy
            wait: (bool) whether to wait/freeze until the order goes through,
                this will cancel orders which do not finish within a timestep
            **kwargs: additional params passed to rbh.buy
        """
        order = self.rbh.buy(self.rbh[symbol], amt, **kwargs)
        if wait:
            self.rbh.wait_for_orders([order], delay=5, timeout=RESOLUTIONS[self.resolution], force=True)
        return order

    def sell(self, symbol, amt, wait=True, **kwargs):
        """Sell stock/currency

        Args:
            symbol: (str) what to sell
            amt: (int) amt to sell
            wait: (bool) whether to wait/freeze until the order goes through,
                this will cancel orders which do not finish within a timestep
            **kwargs: additional params passed to rbh.sell
        """
        order = self.rbh.sell(self.rbh[symbol], amt, **kwargs)
        if wait:
            self.rbh.wait_for_orders([order], delay=5, timeout=RESOLUTIONS[self.resolution], force=True)
        return order
