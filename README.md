# Tradinhood

Programmatically trading stocks and crypto with Robinhood.

## Robinhood

Example Usage:

```python
from Tradinhood import Robinhood
from decimal import Decimal

rbh = Robinhood()

rbh.login(username="l33tTrader", password="pa5s0rd")
# or
rbh.login(token="sPP80a1qYJPdiUdq.fqhQq4yLaH8QIxKqG8eni759DfdZOi2BTZcnbnCB...")

# Use rbh[...] to retrieve stocks and currencies
dogecoin = rbh['DOGE']
apple = rbh['AAPL']

# num shares owned in apple
apple_shares = rbh.quantity(apple)

# Doge is hot rt now so... (WARN: Do NOT run this code)
do_not_run_me() # just in case

# Ditch Apple stock
rbh.sell(apple, apple_shares, type='market')

# A couple mins later...

money_gained = apple_shares * apple.price
print('Sold abt $', money_gained, 'of AAPL')

rbh.buy(dogecoin, money_gained / dogecoin.price, type='limit', price=Decimal('0.0001'))

# Need more doge
rbh.buy(dogecoin, rbh.buying_power / dogecoin.price, type='market')

# Savor your abundant wealth
print(rbh.quantity('DOGE', include_held=True))
# or
print(rbh.get_assets()) # see everything you own as a dict(asset:amt)

# jkjk cancel everything
for order in rbh.orders:
    if order.state == 'confirmed' and order.asset_type == 'cryptocurrency':
        order.cancel()
        rbh.wait_for_orders([order]) # wait for cancel
```

## Dataset

Example Usage:

```python
from Tradinhood import Dataset

# Gather some stock data
dataset = Dataset.from_google('MU', period='1Y', resolution='1d')
dataset |= Dataset.from_google('AMD', period='1Y', resolution='1d') # a |= b to merge from b to a
dataset |= Dataset.from_google('INTC', period='1Y', resolution='1d')
dataset |= Dataset.from_google('GOOG', period='1Y', resolution='1d')
# or use iextrading
dataset2 = Dataset.from_iextrading_charts(['GOOG', 'AAPL'], period='1d', resolution='1m')

# or some crypto data
dataset = Dataset.from_cryptocompare('BTC', resolution='1d', limit=1000)
dataset |= Dataset.from_cryptocompare('ETH', resolution='1d', limit=1000)
dataset |= Dataset.from_cryptocompare('LTC', resolution='1d', limit=1000)

dataset.save('mydata.pkl')
dataset = Dataset.from_file('mydata.pkl')

print(dataset) # <Dataset |BTC,ETH,LTC| (@1d) [2015-11-04T18:00:00 -> 2018-07-31T19:00:00]>

dataset.symbols # ['BTC', 'ETH', 'LTC']

dataset.dates # ['2015-11-04T18:00:00', '2015-11-05T18:00:00', ..., '2018-07-31T19:00:00']

dataset.get('2015-11-04T18:00:00', 'BTC') # OHLCV(...)

dataset.plot(show=True)
```

## Traders

Backtester Usage:

```python
import matplotlib.pyplot as plt
import random

from Tradinhood import Dataset, Backtester

dataset = Dataset.from_file('bitcoin-historical.pkl') # see dataset example

class RandomAlgo(Backtester): # Your algo extends backtester

    def setup(self):
        pass

    def loop(self, date):

        print('My Value/Cash', self.portfolio_value, self.cash)

        for symbol in self.symbols: # Display amt owned, price, and history
            print(symbol, self.quantity(symbol), self.price(symbol))
            print(self.history(symbol, 3))

        stock = random.choice(self.symbols)
        amt = random.randint(-5, 5)

        if amt > 0:
            self.buy(stock, amt)
        if amt < 0:
            self.sell(stock, -amt)

algo = RandomAlgo(symbols=['BTC'])
algo.start(dataset, cash=10000) # Run the algo

f, (ax1, ax2) = plt.subplots(2, sharex=True)
algo.plot(ax1)
algo.plot_assets(ax2)
plt.show()
# or analyze yourself
df = algo.log_as_dataframe()
```

RobinhoodLive Usage:

```python
from Tradinhood import RobinhoodLive

rbh = Robinhood()
rbh.login(username="l33tTrader", password="pa5s0rd") # see robinhood usage

class SellMyDOGE(RobinhoodLive):

    def setup(self):
        pass

    def loop(self, date):
        amt_owned = self.quantity('DOGE')
        amt_to_sell = random.randint(15, amt_owned)
        print(date, 'Selling', amt_to_sell, 'of', amt_owned)
        self.sell('DOGE', amt_to_sell, type='market')

algo = SellMyDOGE(symbols=['DOGE'])
algo.start(rbh, resolution='5m')
# ... you can also use the same methods as the Backtester
```

## Relevant

Unoffical API Docs [sanko/Robinhood](https://github.com/sanko/Robinhood)

Another Robinhood API [Jamonek/Robinhood](https://github.com/Jamonek/Robinhood)

Zipline [zipline-live/zipline](https://github.com/zipline-live/zipline)
