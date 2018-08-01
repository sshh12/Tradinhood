from collections import defaultdict
import matplotlib.pyplot as plt
import pandas as pd
import random
import time

class BaseTrader:

    ### Base Methods ###

    def __init__(self, symbols):
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
        return pd.DataFrame.from_dict(self.log).set_index('datetime')

    def plot(self):
        self.log_as_dataframe().plot()
        plt.show()

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

    def buy(self, symbol, amt):
        return False

    def sell(self, symbol, amt):
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

    def quantity(self, asset):
        return self.owned[asset]

    def price(self, symbol):
        cur_quote = self.dataset.get(self.steps[self.idx], symbol)
        return random.uniform(cur_quote.open, cur_quote.close)

    def history(self, symbol, steps):

        assert self.idx > steps

        hist = []
        for date in self.steps[(self.idx - steps):self.idx]:
            hist.append(self.dataset.get(date, symbol))
        return hist

    def buy(self, symbol, amt):

        price_per = self.price(symbol)
        cost = price_per * amt

        if cost <= self.cash:
            self._cash -= cost
            self.owned[symbol] += amt
            return True
        else:
            return False

    def sell(self, symbol, amt):

        price_per = self.price(symbol)

        if amt <= self.quantity(symbol):
            self._cash += price_per * amt
            self.owned[symbol] -= amt
            return True
        else:
            return False

class Robinhood(BaseTrader):

    pass
