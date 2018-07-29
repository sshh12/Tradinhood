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
```

## Relevant

Helpful Unoffical API Docs [sanko/Robinhood](https://github.com/sanko/Robinhood)

Another Robinhood API [Jamonek/Robinhood](https://github.com/Jamonek/Robinhood)
