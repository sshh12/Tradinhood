# dataset.py
### DatasetException(Exception)
`DatasetException(Exception)`
```
Exception thrown by a dataset method
```
### OHLCV
`OHLCV`
```
OHLCV

Basic class for storing price data at a given timestep.

Attributes:
    open: (float)
    high: (float)
    low: (float)
    close: (float)
    volume: (float)
```
### Dataset
`Dataset`
```
Dataset object

Attributes:
    data: (dict) The internal object data
        stored as `data[timestep][symbol] = OHLCV()`
    resolution: (str) The resolution of the dataset
        which must be a key of `RESOLUTIONS`
    symbols: (list: str) The symbols included in the dataset
```
`Dataset.__init__(self, data, resolution, symbols)`
```
Creates the dataset with predefined params

       This is meant to be called only from the internal `from_...()` class methods
```
`Dataset.from_google(symbol, resolution='1d', period='20d', exchange='NASD')`
```
Fetch data from google

Args:
    symbol: (str) Stock to Fetch
    resolution: (str) The required resolution
        which must be a key of `RESOLUTIONS`
    period: (str) The amount of time to fetch, note:
        google will automatically limit this
    exchange: (str) The stock exchange

Returns:
    (Dataset) with prescribed params and data

Note:
    No longer supported by Google.
```
`Dataset.from_alphavantage(symbol, resolution='1d', api_key='demo')`
```
Fetch data from AlphaVantage

Args:
    symbol: (str) Stock to Fetch
    resolution: (str) The required resolution [5m, 1d]
    api_key: (str) Your API key
Returns:
    (Dataset) with prescribed params and data
```
`Dataset.from_cryptocompare(symbol, resolution='1d', to_symbol='USD', limit=3000, last_unix_time=None)`
```
Fetch data from cryptocompare

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
```
`Dataset.from_robinhood(asset, resolution='1d')`
```
Fetch data from Robinhood

Args:
    asset: (Stock or Crypto) A robinhood Stock/Crypto to fetch
    resolution: (str) The required resolution [15s, 5m, 1d, 1w]

Returns:
    (Dataset) with prescribed params and data
```
`Dataset.from_file(filename)`
```
Load from file

Args:
    filename: (str) The .pkl filename

Returns:
    (Dataset) from the values in the file
```
`Dataset(...).save(self, filename)`
```
Save dataset

Args:
    filename: (str) where to save the dataset
```
`Dataset(...).dates`
```
The dates (in order) that this dataset contains as list: str
```
`Dataset(...).get(self, timestamp, symbol, default=None)`
```
Get datapoint

Args:
    timestamp: (str) a timestamp
    symbol: (str) the symbol of interest
    default: A value if not found
```
`Dataset(...).as_dataframe(self, symbols=None)`
```
Convert to dataframe

Args:
    symbols: (list: str) Symbols to include,
        will default to all in dataset

Returns:
    (Dataframe) with data from dataset
```
`Dataset(...).plot(self, columns=['close'], symbols=None, ax=None, show=False)`
```
Plot

Args:
    columns: (list: str) Columns to plot,
        [open, high, low, close, relclose, relprevclose, volume]
    symbols: (list: str) Symbols to include,
        defaults to all in dataset
    ax: (Axes) Where to plot, defaults to pandas default
    show: (bool) Whether to run plt.show()
```
# endpoints.py
### API
`API`
```
api.robinhood.com
```
### Phoenix
`Phoenix`
```
phoenix.robinhood.com
```
### Nummus
`Nummus`
```
nummus.robinhood.com
```
### Dora
`Dora`
```
dora.robinhood.com
```
# errors.py
### RobinhoodException(Exception)
`RobinhoodException(Exception)`
```
Basic Robinhood exception
```
### APIError(RobinhoodException)
`APIError(RobinhoodException)`
```
An issue interfacing with the Robinhood API
```
### UsageError(RobinhoodException)
`UsageError(RobinhoodException)`
```
An issue using this interface
```
# models.py
### Currency
`Currency`
```
Currency asset object

Attributes:
    json: (dict) internal data json
    name: (str) currency name
    code: (str) currency symbol
    tradable: (bool) if tradable
    type: (str) asset type
    pair_id: (str) currency Pair id
    asset_id: (str) the APIs id for this currency
```
`Currency(...).history(self, bounds='24_7', interval='day', span='year')`
```
Retrieve the price history of this crypto
```
`Currency(...).market_open`
```
Is this crypto's market open
```
`Currency(...).current_quote`
```
Current trade data
```
`Currency(...).price`
```
Current price
```
`Currency(...).ask`
```
Current ask price
```
`Currency(...).bid`
```
Current bid price
```
### Stock
`Stock`
```
Stock asset object

Attributes:
    id: (str) the instrument id for this stock
    chain_id: (str) the id for this stock's options (or None)
    bloomberg_id: (str) the bloomberg id
    json: (dict) internal data json
    name: (str) stock name
    simple_name: (str) simple stock name
    code: (str) currency symbol
    symbol: (str) currency symbol
    tradable: (bool) if tradable
    type: (str) asset type
    instrument_url: (str) the instrument url for this stock
    fractional: (bool) if it supports fractional trading
```
`Stock.from_url(rbh, instrument_url)`
```
Create a stock from its instrument url
```
`Stock.from_id(rbh, id_)`
```
Create a stock from its instrument id
```
`Stock(...).history(self, bounds='regular', interval='day', span='year')`
```
Retrieve the price history of this stock
```
`Stock(...).market_open`
```
If the market for this stock is open
```
`Stock(...).current_quote`
```
Stock quote info
```
`Stock(...).price`
```
Current price
```
`Stock(...).ask`
```
Current ask price
```
`Stock(...).bid`
```
Current bid price
```
`Stock(...).popularity`
```
Get the number of open positions by Robinhood users
```
`Stock(...).earnings`
```
Get the earnings history and estimates
```
`Stock(...).fundamentals`
```
Get stock fundamentals
```
`Stock(...).get_similar`
```
Get similar stocks
```
`Stock(...).get_news(self, pages=1)`
```
Get news for this stock
```
`Stock(...).ratings`
```
Get the overall buy/sell/hold ratings for this stock
```
### Order
`Order`
```
Order object

Attributes:
    json: (dict) internal data json
    id: (str) the order id
    side: (str) buy or sell
    time_in_force: (str) how the order in enforced
    created_at: (str) when the order was created
    quantity: (Decimal) quantity of the asset
    asset_type: (str) cryptocurrency or stock
    cancel_url: (str) the url to cancel the order
    price: (Decimal) the price set in the order,
        this can be None
    stop_price: (Deciaml) the stop price, None if not a stop order
    symbol: (str) the symbol traded in the order, defaults None
    asset: (Stock or Currency) the asset traded in the order, defaults None
```
`Order(...).state`
```
Get order state [confirmed, queued, cancelled, filled]
```
`Order(...).cancel`
```
Cancel this order
```
# robinhood.py
### Robinhood
`Robinhood`
```
Robinhood API interface

Attributes:
    token: (str) API authorization token
    acc_num: (str) Robinhood account number
    nummus_id: (str) The account id associated with currencies
    account_url: (str) The account url
    logged_in: (bool) If successfully authenticated
```
`Robinhood.__init__`
```
Creates session used in client
```
`Robinhood(...).save_login(self, fn='robinhood-login')`
```
Save login to file
```
`Robinhood(...).load_login(self, fn='robinhood-login')`
```
Login from file
```
`Robinhood(...).quantity(self, asset, include_held=False)`
```
Get owned quantity of asset

Args:
    asset: (Currency | Stock | str) the query currency/stock or symbol
    include_held: (bool, optional) whether to included held assets in the tally

Returns:
    (Decimal) Quantity of asset owned

Raises:
    UsageError: If the asset is not valid
```
`Robinhood(...).buy(self, asset, amt, **kwargs)`
```
Buy item

Args:
    asset: (Currency | Stock | str) the asset to be bought
    amt: (Decimal | float | int) the amt to buy
    type: (str, optional) the order type
        ['market', 'limit', 'stoploss', 'stoplimit']
    price: (Decimal | float | int) the order price
    stop_price: (Decimal | float | int) the stop price, required if using stoploss/stoplimit
    time_in_force: (str, optional) when to cancel
        ['gtc', 'gfd', 'ioc', 'opg']
    return_json: (bool) override return with API response

Returns:
    (Order) The order created

Raises:
    UsageError: If used incorrectly...
```
`Robinhood(...).sell(self, asset, amt, **kwargs)`
```
Sell item

Args:
    asset: (Currency | Stock | str) tthe asset to be sold
    amt: (Decimal | float | int) The amt to sell
    type: (str, optional) the order type
        ['market', 'limit', 'stoploss', 'stoplimit']
    price: (Decimal | float | int) the order price
    stop_price: (Decimal | float | int) the stop price, required if using stoploss/stoplimit
    time_in_force: (str, optional) when to cancel
        ['gtc', 'gfd', 'ioc', 'opg']
    return_json: (bool) override return with API response

Returns:
    (Order) The order created

Raises:
    UsageError: If used incorrectly...
```
`Robinhood(...).orders`
```
Get recent order history
```
`Robinhood(...).query_orders(self, sort_by_time=True, include_stocks=True, include_crypto=True, pages=3, lookup_assets=True)`
```
Search orders
```
`Robinhood(...).wait_for_orders(self, orders, delay=5, timeout=120, force=False)`
```
Sleep until order is complete

Args:
    orders: (list: Order) the orders to wait for
    delay: (int) time in seconds between checks
    timeout: (int) time in seconds to give up waiting
    force: (bool) cancel all orders which were not completed in time

Returns:
    (bool) if the orders where complete
```
`Robinhood(...).get_assets(self, include_positions=True, include_holdings=True, include_held=False, include_zero=False)`
```
Get all owned assets

Args:
    include_positions: (bool) whether to include stocks
    include_holdings: (bool) whether to include currencies
    include_held: (bool) whether to include held assets
    include_zero: (bool) whether to include assets with zero quantity

Returns:
    (dict) Stock or Currency objects paired with quantities
```
`Robinhood(...).account_info`
```
Account info
```
`Robinhood(...).holdings`
```
Currency holdings
```
`Robinhood(...).positions`
```
Share positions
```
`Robinhood(...).withdrawable_cash`
```
Cash that can be withdrawn
```
`Robinhood(...).buying_power`
```
Buying power
```
`Robinhood(...).cash`
```
Cash
```
`Robinhood(...).unsettled_funds`
```
Unsettled funds
```
`Robinhood(...).get_stocks_by_tag(self, tag)`
```
Get stock list by tag

Args:
    tag: (str) The tag to use (exs. top-movers, 100-most-popular)

Returns:
    (tuple str, list<Stock>) The name and list of stocks
```
`Robinhood(...).history(self, bounds='trading', interval='5minute', span='day', account_id=None)`
```
Get portfolio value history

Args:
    bounds: (str) The bounds for the returned price data
    interval: (str) The resolution of the data
    span: (str) The span of time to get data for
    account_id: (str, optional) The account id of the portfolio

Returns:
    (dict) Portfolio price data
```
`Robinhood(...).unified_data`
```
Get the unified data of the account
```
`Robinhood(...).user_data`
```
Get the data about the account user
```
`Robinhood(...).get_bulk_prices(self, stocks, bounds='trading', include_inactive=True)`
```
Get the prices of multiple stocks at the same time

Args:
    stocks: (list<Stock>) Stocks to find prices for
    bounds: (str) The bounds for the returned price data
    include_inactive: (str) Include inactive stocks

Returns:
    (dict) Price data
```
`Robinhood(...).get_bulk_popularity(self, stocks)`
```
Get the popularity of multiple stocks at the same time

Args:
    stocks: (list<Stock>) Stocks to find popularity for

Returns:
    (dict) Popularity data
```
`Robinhood(...).get_bulk_ratings(self, stocks)`
```
Get the ratings of multiple stocks at the same time

Args:
    stocks: (list<Stock>) Stocks to find ratings for

Returns:
    (dict) Ratings data
```
# traders.py
### BaseTrader
`BaseTrader`
```
The abstract trader

Attributes:
    log: (dict) a log containing time, cash, and assets
    symbols: (list: str) the symbols tracked
```
`BaseTrader.__init__(self, symbols)`
```
Create trader

       Only symbols required, the rest of init is done with .start(...)
```
`BaseTrader(...).log_as_dataframe`
```
Convert log to a pandas DataFrame

Returns:
    (DataFrame)
```
`BaseTrader(...).plot(self, columns=['end_portfolio_value', 'end_cash'], ax=None, show=False)`
```
Plot money

Args:
    columns: (list: str) the columns to plot, use .log to find columns
    ax: (Axis) where to plot, defaults to pandas
    show: (bool) display the plot
```
`BaseTrader(...).plot_assets(self, symbols=None, ax=None, show=False)`
```
Plot assets

Args:
    symbols: (list: str) the symbols to include, defaults to all
    ax: (Axis) where to plot, defaults to pandas
    show: (bool) display the plot
```
`BaseTrader(...).start(self, *args, **kwargs)`
```
Start.

       Universal start method implemented by Traders
```
`BaseTrader(...).cash`
```
Cash/Buying power
```
`BaseTrader(...).portfolio_value`
```
Portfolio value (cash + stocks + currencies)
```
`BaseTrader(...).quantity(self, symbol)`
```
The owned quantity of symbol
```
`BaseTrader(...).set_quantity(self, symbol, amt)`
```
Will buy or sell to set quantity of symbol
```
`BaseTrader(...).price(self, symbol)`
```
Find price of symbol
```
`BaseTrader(...).buy(self, symbol, amt, **kwargs)`
```
Buy symbol
```
`BaseTrader(...).sell(self, symbol, amt, **kwargs)`
```
Sell symbol
```
`BaseTrader(...).history(self, symbol, steps)`
```
Get history of symbol over steps * resolution
```
`BaseTrader(...).setup`
```
Will run before trading.

       Override with algorithm but do not call (handled by .start(...))
```
`BaseTrader(...).loop(self, current_date)`
```
Will run at each timestep

       Override with algorithm but do not call (handled by .start(...))
```
`BaseTrader(...).clean_up`
```
Will run when algo is done running.

       Override with algorithm but do not call (handled by .start(...))
```
### Backtester(BaseTrader)
`Backtester(BaseTrader)`
```
A backtester

A trader which uses predetermined data from testing an algo.

Attributes:
    dataset: (Dataset) the dataset used
    steps: (list: str) the timestamps covered by the dataset
```
`Backtester(BaseTrader)(...).start(self, dataset, cash=10000, start_idx=50)`
```
Start the backtesting

Args:
    dataset: (Dataset) the dataset to use
    cash: (int) starting cash amt
    start_idx: (int) the timestep in the dataset to start, used to ensure
    .history() with have data to return
```
`Backtester(BaseTrader)(...).price(self, symbol)`
```
Randomly determines price based on dataset
```
`Backtester(BaseTrader)(...).buy(self, symbol, amt, **kwargs)`
```
Simulates a buy
```
`Backtester(BaseTrader)(...).sell(self, symbol, amt, **kwargs)`
```
Simulates a sell
```
### Robinhood(BaseTrader)
`Robinhood(BaseTrader)`
```
A Robinhood trader

A trader which uses Robinhood to execute the trades (IRL)

Attributes:
    rbh: (Robinhood*) a robinhood client
    resolution: (str) the trade resolution/frequency
```
`Robinhood(BaseTrader)(...).start(self, robinhood, resolution='1d', until=None)`
```
Starts live trading

Args:
    robinhood: (Robinhood*) a robinhood client, that already has logged in
    resolution: (str) the resolution/freq to trade at
    until: (str) a timestamp at which to stop trading, defaults to forever
```
`Robinhood(BaseTrader)(...).portfolio_value`
```
Calc portfolio value based on robinhood assets
```
`Robinhood(BaseTrader)(...).cash`
```
Robinhood buying power
```
`Robinhood(BaseTrader)(...).price(self, symbol)`
```
The price according to the Robinhood API
```
`Robinhood(BaseTrader)(...).buy(self, symbol, amt, wait=True, **kwargs)`
```
Buy stock/currency

Args:
    symbol: (str) what to buy
    amt: (int) amt to buy
    wait: (bool) whether to wait/freeze until the order goes through,
        this will cancel orders which do not finish within a timestep
    **kwargs: additional params passed to rbh.buy
```
`Robinhood(BaseTrader)(...).sell(self, symbol, amt, wait=True, **kwargs)`
```
Sell stock/currency

Args:
    symbol: (str) what to sell
    amt: (int) amt to sell
    wait: (bool) whether to wait/freeze until the order goes through,
        this will cancel orders which do not finish within a timestep
    **kwargs: additional params passed to rbh.sell
```