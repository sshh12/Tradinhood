from collections import defaultdict
import matplotlib.pyplot as plt
import pandas as pd
import time

class BaseTrader:

    ### Base Methods ###

    def __init__(self, symbols, cash=10000):
        self.cash = cash
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

        for symbol in self.symbols:
            self.log['end_owned_' + symbol].append(self.quantity(symbol))

    def log_as_dataframe(self):
        return pd.DataFrame.from_dict(self.log)

    def plot(self):
        self.log_as_dataframe().plot()
        plt.show()

    ### Runner Methods ###

    def start(self, *args, **kwargs):
        pass

    ### Trading Methods ###

    @property
    def portfolio_value(self):
        pass

    def quantity(self, symbol):
        pass

    def price(self, symbol):
        pass

    def buy(self, symbol, amt):
        pass

    ### Algo Code ###

    def setup(self):
        pass

    def loop(self, current_date):
        pass

class Backtester(BaseTrader):

    def start(self, dataset):

        self.dataset = dataset
        self.steps = self.dataset.dates
        self.idx = 0
        self.owned = defaultdict(lambda: 0)

        self.setup()

        for i, current_date in enumerate(self.steps):
            self.idx = i
            self._step(current_date)

    @property
    def portfolio_value(self):

        value = self.cash

        for symbol in self.symbols:
            value += self.quantity(symbol) * self.price(symbol)

        return value

    def quantity(self, asset):
        return self.owned[asset]

    def price(self, symbol):
        return self.dataset.get(self.steps[self.idx], symbol).open

    def buy(self, symbol, amt):

        price_per = self.price(symbol)
        cost = price_per * amt

        if cost <= self.cash:
            self.cash -= cost
            self.owned[symbol] += amt
            return True
        else:
            return False

# class Robinhood(BaseTrader):
#
#     def start(self):
#
#         self.setup()
#
#         while True:
#             time.sleep(60)
#             self.loop()
