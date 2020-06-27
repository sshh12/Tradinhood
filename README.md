# Tradinhood

Programmatically trading stocks and crypto with Robinhood.

```shell
$ pip install git+https://github.com/sshh12/Tradinhood.git --upgrade
```

[Docs](https://github.com/sshh12/Tradinhood/blob/master/docs/DOCS.md)

## Robinhood

Example Usage:

```python
from tradinhood import Robinhood
from decimal import Decimal
import random

rbh = Robinhood()

rbh.login(username="l33tTrader", password="pa5s0rd")
rbh.save_login()
# or
rbh.login(token="sPP80a1qYJPdiUdq.fqhQq4yLaH8QIxKqG8eni759DfdZOi2BTZcnbnCB...")
rbh.save_login()
# or
rbh.load_login()

# Use rbh[...] to retrieve stocks and currencies
dogecoin = rbh['DOGE']
apple = rbh['AAPL']

# num shares owned in apple
apple_shares = rbh.quantity(apple)

# See more info about AAPL
print(apple.popularity)
print(apple.ratings)
print(apple.earnings)
print(apple.fundamentals)
print(apple.get_similar())
print(apple.get_news())

# Check options
for option in apple.puts:
    print(option.iv)
    print(option.greeks)

# (WARN: Do NOT run this code)
do_not_run_me() # just in case

random_option = random.choice(apple.puts)
rbh.order_options([('buy', random_option, 'open')], quantity=1, price=4.20)

# Time to switch to Dogecoin...ditch Apple stock
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

# also
_, movers = rbh.get_stocks_by_tag('top-movers')
print(rbh.get_bulk_popularity(movers))

# See how you've gained/lost money over time
print(rbh.history())
```

```python
from tradinhood.tools import order_profit_loss

print(order_profit_loss(rbh, pages=3, include_options=False))
```

## Relevant

Unoffical API Docs [sanko/Robinhood](https://github.com/sanko/Robinhood)

Another Robinhood API [Jamonek/Robinhood](https://github.com/Jamonek/Robinhood)
