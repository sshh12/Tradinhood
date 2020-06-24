from decimal import getcontext, Decimal
from datetime import datetime
import requests
import time
import uuid


# The API seems to use 18 digits, so I copied that
getcontext().prec = 18


ENDPOINTS = {
    'token': 'https://api.robinhood.com/oauth2/token/',
    'challenge': 'https://api.robinhood.com/challenge/',
    'accounts': 'https://api.robinhood.com/accounts/',
    'quotes': 'https://api.robinhood.com/quotes/',
    'orders': 'https://api.robinhood.com/orders/',
    'news': 'https://api.robinhood.com/midlands/news/',
    'fundamentals': 'https://api.robinhood.com/marketdata/fundamentals/',
    'instruments': 'https://api.robinhood.com/instruments/',
    'positions': 'https://api.robinhood.com/positions/',
    'historicals': 'https://api.robinhood.com/marketdata/historicals/',
    'earnings': 'https://api.robinhood.com/marketdata/earnings/',
    'nummus_historicals': 'https://api.robinhood.com/marketdata/forex/historicals/',
    'port_historicals': 'https://api.robinhood.com/portfolios/historicals/',
    'forex_market_quote': 'https://api.robinhood.com/marketdata/forex/quotes/',
    'tags': 'https://api.robinhood.com/midlands/tags/tag/',
    'ratings': 'https://api.robinhood.com/midlands/ratings/',
    'popularity': 'https://api.robinhood.com/instruments/popularity/',
    'ratings': 'https://api.robinhood.com/midlands/ratings/',
    'user': 'https://api.robinhood.com/user/',
    'unified': 'https://phoenix.robinhood.com/accounts/unified',
    'instruments_similar': 'https://dora.robinhood.com/instruments/similar/',
    'holdings': 'https://nummus.robinhood.com/holdings/',
    'nummus_orders': 'https://nummus.robinhood.com/orders/',
    'currency_pairs': 'https://nummus.robinhood.com/currency_pairs/',
    'nummus_accounts': 'https://nummus.robinhood.com/accounts/'
}


API_HEADERS = {  # Default header params
    'Accept': '*/*',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'X-Robinhood-API-Version': '1.221.0'
}


# Extracted from robinhood web app
OAUTH_CLIENT_ID = 'c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS'


class RobinhoodException(Exception):
    """Basic Robinhood exception"""
    pass


class APIError(RobinhoodException):
    """An issue interfacing with the Robinhood API"""
    pass


class UsageError(RobinhoodException):
    """An issue using this interface"""
    pass


class Robinhood:
    """Robinhood API interface

    Attributes:
        token: (str) API authorization token
        acc_num: (str) Robinhood account number
        nummus_id: (str) The account id associated with currencies
        account_url: (str) The account url
        logged_in: (bool) If successfully authenticated
    """
    token = None
    acc_num = None
    nummus_id = None
    account_url = None
    logged_in = False

    def __init__(self):
        """Creates session used in client"""
        self.session = requests.session()
        self.session.headers = API_HEADERS
        self.device_token = str(uuid.uuid4())
        self._load()

    def _load(self):
        """Inits basic internal information"""
        asset_currs = self._get_pagination(ENDPOINTS['currency_pairs'], auth=False)
        for curr_json in asset_currs:
            currency = Currency(self.session, curr_json)

    def _get_pagination(self, start_url, auth=True, pages=100):
        results = []
        cur_url = start_url
        i = 0
        while cur_url is not None and i < pages:
            if auth:
                resp = self._get_authed(cur_url)
            else:
                resp = self._get_unauthed(cur_url)
            results.extend(resp['results'])
            pages += 1
            cur_url = resp.get('next')
        return results

    def _get_unauthed(self, url):
        try:
            res = self.session.get(url)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            raise APIError('Unable to access endpoint {} (got {})'.format(url, e))

    def _get_authed(self, url):
        assert self.logged_in
        try:
            res = self.session.get(url)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            raise APIError('Unable to access endpoint {} (got {})'.format(url, e))

    def _load_auth(self, acc_num=None, nummus_id=None):
        """Inits internal account information from Robinhood

        Args:
            acc_num: (str, optional) manually specify the account number
            nummus_id: (str, optional) manually specify the nummus id

        Raises:
            APIError: If logged in but no account found
        """
        assert self.logged_in
        try:
            if not acc_num:
                res_json = self._get_pagination(ENDPOINTS['accounts'])
                if len(res_json) == 0:
                    raise APIError('No robinhood accounts found. ' +
                                   'You may still be in the process of being verified.')
                self.acc_num = res_json[0]['account_number']
            else:
                self.acc_num = acc_num
            self.account_url = ENDPOINTS['accounts'] + self.acc_num + '/'
            if not nummus_id:
                res_nummus_json = self._get_pagination(ENDPOINTS['nummus_accounts'])
                if len(res_nummus_json) == 0:
                    raise APIError('No robinhood crypto accounts found. ' +
                                   'Try buying some online to get this part of your account activated.')
                self.nummus_id = res_nummus_json[0]['id']
            else:
                self.nummus_id = nummus_id
        except KeyError:
            raise APIError('Unable to load secure content (retry login)')

    def login(self, token='', username='', password='', mfa_code='', verification='sms', acc_num=None, nummus_id=None):
        """Login/Authenticate

        Args:
            token: (str) required if username/password not given, bypasses login
                since API token already known
            username: (str) required login information if token not specified
            password: (str) required login information if token not specified
            mfa_code: (str) 2 Factor code, required if enabled on the account
            verification: (str) The type of verification to use if required [sms, email]
            acc_num: (str, optional) manual specify the account number
            nummus_id: (str, optional) manual specify the nummus id

        Returns:
            (bool) If login was successful

        Raises:
            APIError: If login fails
        """
        if token:  # Skip login
            self.token = token
            self.session.headers['Authorization'] = 'Bearer ' + self.token
            self.logged_in = True
            self._load_auth(acc_num)
            return True

        if not username or not password:  # If not provided, manually prompt
            import getpass
            username = input('Username: ')
            password = getpass.getpass('Password (Hidden): ')

        req_json = {
            'client_id': OAUTH_CLIENT_ID,
            'expires_in': 86400,
            'grant_type': 'password',
            'scope': 'internal',
            'username': username,
            'password': password,
            'device_token': self.device_token,
            'challenge_type': verification
        }

        if mfa_code:
            req_json['mfa_code'] = mfa_code

        res_json = {}
        try:
            res = self.session.post(ENDPOINTS['token'], json=req_json)
            res_json = res.json()
            if 'detail' in res_json and 'challenge issued' not in res_json['detail']:
                res.raise_for_status()
        except Exception:
            raise APIError('Login failed ' + str(res_json))

        if 'detail' in res_json and 'challenge issued' in res_json['detail']:
            code = input('Verification Code: ')
            challenge_id = res_json['challenge']['id']
            challenge_res = self.session.post(
                ENDPOINTS['challenge'] + challenge_id + '/respond/', json={'response': code})
            if challenge_res.json()['status'] != 'validated':
                raise APIError('Provided challenge code failed.')
            self.session.headers['X-ROBINHOOD-CHALLENGE-RESPONSE-ID'] = challenge_id
            try:
                res = self.session.post(ENDPOINTS['token'], json=req_json)
                res.raise_for_status()
                res_json = res.json()
            except Exception:
                raise APIError('Challenge auth failed')

        if 'mfa_required' in res_json and res_json['mfa_required']:
            mfa_code = input('MFA Code: ')
            req_json['mfa_code'] = mfa_code
            try:
                res = self.session.post(ENDPOINTS['token'], json=req_json)
                res.raise_for_status()
                res_json = res.json()
            except Exception:
                raise APIError('MFA auth failed')

        if 'access_token' in res_json:
            self.token = res_json['access_token']
            self.session.headers['Authorization'] = 'Bearer ' + self.token
            self.logged_in = True
            self._load_auth(acc_num, nummus_id)
            return True

        return False

    def save_login(self, fn='robinhood-login'):
        """Save login to file"""
        with open(fn, 'w') as save_fp:
            save_fp.write(self.token)

    def load_login(self, fn='robinhood-login'):
        """Login from file"""
        with open(fn, 'r') as save_fp:
            token = save_fp.read()
        self.login(token=token)

    def __repr__(self):
        return '<Robinhood [Account: {}]>'.format(self.acc_num)

    def __getitem__(self, symbol):
        """Access items using robinhood[symbol]

        Args:
            symbol: (str) The currency or stock symbol, ex. AMZN, DOGE

        Returns:
            (Currency | Stock) The object associated with that symbol

        Raises:
            APIError: If symbol cannot be associated with a stock or currency
        """
        if symbol in Currency.cache:
            return Currency.cache[symbol]
        if symbol in Stock.cache:
            return Stock.cache[symbol]
        try:
            results = self._get_pagination(ENDPOINTS['instruments'] + '?active_instruments_only=false&symbol=' + symbol)
            stock = Stock(self.session, results[0])
            return stock
        except Exception:
            raise APIError('Unable to find asset')

    def quantity(self, asset, include_held=False):
        """Get owned quantity of asset

        Args:
            asset: (Currency | Stock | str) the query currency/stock or symbol
            include_held: (bool, optional) whether to included held assets in the tally

        Returns:
            (Decimal) Quantity of asset owned

        Raises:
            UsageError: If the asset is not valid
        """
        assert self.logged_in
        if isinstance(asset, str):  # convert str to Stock or Currency
            asset = self.__getitem__(asset)
        if isinstance(asset, Currency):
            assets = self.get_assets(
                include_positions=False, include_holdings=True, include_held=include_held)
        elif isinstance(asset, Stock):
            assets = self.get_assets(
                include_positions=True, include_holdings=False, include_held=include_held)
        else:
            raise UsageError('Invalid asset type')
        # default to zero if not in positions or holdings
        return assets.get(asset, Decimal('0.00'))

    def _order(self, order_side, asset, amt, type='market', price=None, stop_price=None, time_in_force='gtc', return_json=False):
        """Internal order method

        See .buy(...) and .sell(...)
        """
        assert self.logged_in
        assert order_side in ['buy', 'sell']
        assert time_in_force in ['gtc', 'gfd', 'ioc', 'opg']

        if isinstance(asset, str):
            asset = self.__getitem__(asset)

        assert asset.tradable

        if price is None:
            price = asset.price
        price = str(price)

        if isinstance(asset, Currency):

            assert type in ['market', 'limit']
            assert stop_price is None

            amt = str(amt)

            req_json = {
                'type': type,
                'side': order_side,
                'quantity': amt,
                'account_id': self.nummus_id,
                'currency_pair_id': asset.pair_id,
                'price': price,
                'ref_id': str(uuid.uuid4()),  # Generated temp id
                'time_in_force': time_in_force
            }

            res = self.session.post(ENDPOINTS['nummus_orders'], json=req_json)
            res_json = res.json()

            if 'error_code' in res_json:
                raise APIError(res_json['error_code'])

            if return_json:
                return res_json
            else:
                return Order(self.session, res_json, 'cryptocurrency', symbol=asset.symbol, asset=asset)

        elif isinstance(asset, Stock):

            assert type in ['market', 'limit', 'stoploss', 'stoplimit']

            # Convert types into correct parameters
            order_type = 'market' if (
                type in ['market', 'stoploss']) else 'limit'
            trigger = 'immediate' if (type in ['market', 'limit']) else 'stop'

            amt = str(round(amt, 0))  # Shares must be integers

            if trigger == 'stop':
                assert stop_price
                stop_price = str(stop_price)
            else:
                assert stop_price is None

            req_json = {
                'time_in_force': time_in_force,
                'price': price,
                'quantity': amt,
                'side': order_side,
                'trigger': trigger,
                'type': order_type,
                'account': self.account_url,
                'instrument': asset.instrument_url,
                'symbol': asset.symbol,
                'ref_id': str(uuid.uuid4()),  # Generated temp id
                'extended_hours': False  # not sure what this is
            }

            if stop_price:
                req_json['stop_price'] = stop_price

            res = self.session.post(ENDPOINTS['orders'], json=req_json)
            res_json = res.json()

            if 'error_code' in res_json:
                raise APIError(res_json['error_code'])

            if return_json:
                return res_json
            else:
                return Order(self.session, res_json, 'stock', symbol=asset.symbol, asset=asset)

        else:
            raise UsageError('Invalid asset')

    def buy(self, asset, amt, **kwargs):
        """Buy item

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
        """
        return self._order('buy', asset, amt, **kwargs)

    def sell(self, asset, amt, **kwargs):
        """Sell item

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
        """
        return self._order('sell', asset, amt, **kwargs)

    @property
    def orders(self):
        """Get recent order history"""
        return self.query_orders()

    def query_orders(self, sort_by_time=True, include_stocks=True, include_crypto=True, pages=3, lookup_assets=True):
        """Search orders"""
        if include_stocks:
            json_stocks = self._get_pagination(ENDPOINTS['orders'], pages=pages)
        if include_crypto:
            json_crypto = self._get_pagination(ENDPOINTS['nummus_orders'], pages=pages)
        orders = []
        orders += [Order(self.session, json_data, 'stock', lookup_asset=lookup_assets)
                   for json_data in json_stocks]
        orders += [Order(self.session, json_data, 'cryptocurrency')
                   for json_data in json_crypto]
        if sort_by_time:
            orders.sort(key=lambda o: o.created_at)
        return orders

    def wait_for_orders(self, orders, delay=5, timeout=120, force=False):
        """Sleep until order is complete

        Args:
            orders: (list: Order) the orders to wait for
            delay: (int) time in seconds between checks
            timeout: (int) time in seconds to give up waiting
            force: (bool) cancel all orders which were not completed in time

        Returns:
            (bool) if the orders where complete
        """
        def order_complete(order):
            return order.state in ['filled', 'cancelled']
        checks = timeout // delay
        while not all(map(order_complete, orders)) and checks > 0:
            time.sleep(delay)
            checks -= 1
        if force:
            for order in orders:
                if order.state in ['confirmed', 'queued']:
                    order.cancel()
        return all(map(order_complete, orders))

    def get_assets(self, include_positions=True, include_holdings=True, include_held=False, include_zero=False):
        """Get all owned assets

        Args:
            include_positions: (bool) whether to include stocks
            include_holdings: (bool) whether to include currencies
            include_held: (bool) whether to include held assets
            include_zero: (bool) whether to include assets with zero quantity

        Returns:
            (dict) Stock or Currency objects paired with quantities
        """
        assert self.logged_in

        my_assets = {}

        if include_positions:
            stocks = self.positions
            for stock_json in stocks:
                stock = Stock.from_url(self.session, stock_json['instrument'])
                amt = Decimal(stock_json['quantity'])
                if include_held:
                    amt += Decimal(stock_json['shares_held_for_buys'])
                    amt += Decimal(stock_json['shares_held_for_sells'])
                    amt += Decimal(stock_json['shares_held_for_options_collateral'])
                    amt += Decimal(stock_json['shares_held_for_options_events'])
                    amt += Decimal(stock_json['shares_held_for_stock_grants'])
                if include_zero or amt > 0:
                    my_assets[stock] = amt

        if include_holdings:
            currs = self.holdings
            for curr_json in currs:
                code = curr_json['currency']['code']
                if code in Currency.cache:  # all currencies already cached
                    curr = Currency.cache[code]
                    amt = Decimal(curr_json['quantity_available'])
                    if include_held:
                        amt += Decimal(curr_json['quantity_held_for_buy'])
                        amt += Decimal(curr_json['quantity_held_for_sell'])
                    if include_zero or amt > 0:
                        my_assets[curr] = amt

        return my_assets

    @property
    def account_info(self):
        """Account info"""
        assert self.acc_num is not None
        return self._get_authed(ENDPOINTS['accounts'] + self.acc_num)

    @property
    def holdings(self):
        """Currency holdings"""
        return self._get_pagination(ENDPOINTS['holdings'])

    @property
    def positions(self):
        """Share positions"""
        return self._get_pagination(ENDPOINTS['positions'])

    @property
    def withdrawable_cash(self):
        """Cash that can be withdrawn"""
        return Decimal(self.account_info['cash_available_for_withdrawal'])

    @property
    def buying_power(self):
        """Buying power"""
        return Decimal(self.account_info['buying_power'])

    @property
    def cash(self):
        """Cash"""
        return Decimal(self.account_info['cash'])

    @property
    def unsettled_funds(self):
        """Unsettled funds"""
        return Decimal(self.account_info['unsettled_funds'])

    def get_stocks_by_tag(self, tag):
        """Get stock list by tag

        Args:
            tag: (str) The tag to use (exs. top-movers, 100-most-popular)

        Returns:
            (tuple str, list<Stock>) The name and list of stocks
        """
        resp_json = self._get_authed(ENDPOINTS['tags'] + tag + '/')
        name = resp_json['name']
        stocks = [Stock.from_url(self.session, url)
                  for url in resp_json['instruments']]
        return (name, stocks)

    def history(self, bounds='trading', interval='5minute', span='day', account_id=None):
        """Get portfolio value history

        Args:
            bounds: (str) The bounds for the returned price data
            interval: (str) The resolution of the data
            span: (str) The span of time to get data for
            account_id: (str, optional) The account id of the portfolio

        Returns:
            (dict) Portfolio price data
        """
        assert self.logged_in
        if account_id is None:
            account_id = self.acc_num
        url = ENDPOINTS['port_historicals'] \
            + '{0}/?account={0}&bounds={1}&interval={2}&span={3}'\
            .format(account_id, bounds, interval, span)
        return self._get_authed(url)

    @property
    def unified_data(self):
        """Get the unified data of the account"""
        return self._get_authed(ENDPOINTS['unified'])

    @property
    def user_data(self):
        """Get the data about the account user"""
        return self._get_authed(ENDPOINTS['user'])

    def get_bulk_prices(self, stocks, bounds='trading', include_inactive=True):
        """Get the prices of multiple stocks at the same time

        Args:
            stocks: (list<Stock>) Stocks to find prices for
            bounds: (str) The bounds for the returned price data
            include_inactive: (str) Include inactive stocks

        Returns:
            (dict) Price data
        """
        assert len(stocks) > 0
        instrument_urls = ','.join([stock.instrument_url for stock in stocks])
        url = (ENDPOINTS['quotes'] +
               '?bounds={}&include_inactive={}&instruments={}'
               .format(bounds, str(include_inactive).lower(), instrument_urls))
        results = self._get_pagination(url)
        prices = {}
        for stock in stocks:
            stock_data = None
            for item in results:
                if item['symbol'] == stock.symbol:
                    stock_data = item
                    break
            prices[stock] = stock_data
        return prices

    def get_bulk_popularity(self, stocks):
        """Get the popularity of multiple stocks at the same time

        Args:
            stocks: (list<Stock>) Stocks to find popularity for

        Returns:
            (dict) Popularity data
        """
        assert len(stocks) > 0
        instrument_ids = ','.join([stock.id for stock in stocks])
        url = (ENDPOINTS['popularity'] +
               '?ids={}'.format(instrument_ids))
        results = self._get_pagination(url)
        pop = {}
        for item in results:
            item_stock = None
            for stock in stocks:
                if item['instrument'] == stock.instrument_url:
                    item_stock = stock
                    break
            pop[item_stock] = item['num_open_positions']
        return pop

    def get_bulk_ratings(self, stocks):
        """Get the ratings of multiple stocks at the same time

        Args:
            stocks: (list<Stock>) Stocks to find ratings for

        Returns:
            (dict) Ratings data
        """
        assert len(stocks) > 0
        instrument_ids = ','.join([stock.id for stock in stocks])
        url = (ENDPOINTS['ratings'] +
               '?ids={}'.format(instrument_ids))
        results = self._get_pagination(url)
        ratings = {}
        for item in results:
            item_stock = None
            for stock in stocks:
                if item['instrument_id'] == stock.id:
                    item_stock = stock
                    break
            ratings[item_stock] = item['summary']
        return ratings


class Currency:
    """Currency asset object

    Attributes:
        session: (Session) current session used by the API
        json: (dict) internal data json
        name: (str) currency name
        code: (str) currency symbol
        tradable: (bool) if tradable
        type: (str) asset type
        pair_id: (str) currency Pair id
        asset_id: (str) the APIs id for this currency
    """
    cache = {}

    def __init__(self, session, asset_json):

        self.session = session
        self.json = asset_json

        self.name = self.json['asset_currency']['name']
        self.code = self.json['asset_currency']['code']
        self.symbol = self.json['symbol']
        self.tradable = (self.json['tradability'] == 'tradable')
        self.type = self.json['asset_currency']['type']
        self.pair_id = self.json['id']
        self.asset_id = self.json['asset_currency']['id']

        Currency.cache[self.code] = self

    def history(self, bounds='24_7', interval='day', span='year'):
        """Retrieve the price history of this crypto"""
        try:
            res = self.session.get(ENDPOINTS['nummus_historicals'] +
                                   '{}/?bounds={}&interval={}&span={}'.format(self.pair_id, bounds, interval, span))
            return res.json()['data_points']
        except Exception:
            raise APIError('Unable to access historical market data')

    @property
    def market_open(self):
        """Is this crypto's market open"""
        return True  # I think its always open...

    @property
    def current_quote(self):
        """Current trade data"""
        try:
            res = self.session.get(
                ENDPOINTS['forex_market_quote'] + self.pair_id + '/')
            res.raise_for_status()
            return res.json()
        except Exception:
            raise APIError('Unable to access currency data')

    @property
    def price(self):
        """Current price"""
        return Decimal(self.current_quote['mark_price'])

    @property
    def ask(self):
        """Current ask price"""
        return Decimal(self.current_quote['ask_price'])

    @property
    def bid(self):
        """Current bid price"""
        return Decimal(self.current_quote['bid_price'])

    def __hash__(self):
        return hash(self.type + self.code)

    def __eq__(self, other):
        return isinstance(other, Currency) and other.code == self.code

    def __repr__(self):
        return f'<Currency ({self.name}) [{self.code}]>'


class Stock:
    """Stock asset object

    Attributes:
        session: (Session) current session used by the API
        json: (dict) internal data json
        name: (str) stock name
        simple_name: (str) simple stock name
        code: (str) currency symbol
        symbol: (str) currency symbol
        tradable: (bool) if tradable
        type: (str) asset type
        instrument_url: (str) the instrument url for this stock
        id: (str) the APIs id for this stock
    """
    cache = {}

    def __init__(self, session, instrument_json):

        self.session = session
        self.json = instrument_json

        self.id = self.json['id']
        self.name = self.json['name']
        self.simple_name = self.json['simple_name']
        self.symbol = self.json['symbol']
        self.code = self.symbol
        self.tradable = self.json['tradeable']
        self.type = self.json['type']
        self.instrument_url = ENDPOINTS['instruments'] + self.id + '/'
        self.market_url = self.json['market']

        Stock.cache[self.symbol] = self

    @staticmethod
    def from_url(session, instrument_url):
        """Create a stock from its instrument url"""
        for symbol, stock in Stock.cache.items():  # try cache
            if stock.id in instrument_url:
                return stock

        return Stock(session, session.get(instrument_url).json())

    @staticmethod
    def from_id(session, id_):
        """Create a stock from its instrument id"""
        return Stock.from_url(session, ENDPOINTS['instruments'] + id_ + '/')

    def history(self, bounds='regular', interval='day', span='year'):
        """Retrieve the price history of this stock"""
        try:
            res = self.session.get(ENDPOINTS['historicals'] +
                                   '{}/?bounds={}&interval={}&span={}'.format(self.symbol, bounds, interval, span))
            return res.json()['historicals']
        except Exception:
            raise APIError('Unable to access historical market data')

    @property
    def market_open(self):
        """If the market for this stock is open"""
        try:
            res = self.session.get(
                self.market_url + 'hours/' + datetime.today().isoformat()[:10] + '/')
            res.raise_for_status()
            return res.json()['is_open']
        except Exception:
            raise APIError('Unable to access market data')

    @property
    def current_quote(self):
        """Stock quote info"""
        try:
            res = self.session.get(ENDPOINTS['quotes'] + self.symbol + '/')
            res.raise_for_status()
            return res.json()
        except Exception:
            raise APIError('Unable to access stock data')

    @property
    def price(self):
        """Current price"""
        return Decimal(self.current_quote['last_trade_price'])

    @property
    def ask(self):
        """Current ask price"""
        return Decimal(self.current_quote['ask_price'])

    @property
    def bid(self):
        """Current bid price"""
        return Decimal(self.current_quote['bid_price'])

    @property
    def popularity(self):
        """Get the number of open positions by Robinhood users"""
        try:
            res = self.session.get(self.instrument_url + 'popularity/')
            res.raise_for_status()
            return Decimal(res.json()['num_open_positions'])
        except Exception:
            raise APIError('Unable to access popularity data')

    @property
    def earnings(self):
        """Get the earnings history and estimates"""
        try:
            res = self.session.get(ENDPOINTS['earnings'] +
                                   '?instrument=/instruments/' + self.id + '/')
            res.raise_for_status()
            results = res.json()['results']
            earnings = []
            for item in results:
                earning = {}
                for key in ['year', 'quarter', 'eps', 'report', 'call']:
                    earning[key] = item[key]
                earnings.append(earning)
            return earnings
        except Exception:
            raise APIError('Unable to access earnings data')

    @property
    def fundamentals(self):
        """Ges"""
        try:
            res = self.session.get(ENDPOINTS['fundamentals'] +
                                   self.id + '/?include_inactive=true')
            res.raise_for_status()
            return res.json()
        except Exception:
            raise APIError('Unable to get fundamentals')

    def get_similar(self):
        """Get similar stocks"""
        try:
            res = self.session.get(
                ENDPOINTS['instruments_similar'] + self.id + '/')
            res.raise_for_status()
            results = res.json()['similar']
            stocks = []
            for item in results:
                stocks.append(Stock.from_id(
                    self.session, item['instrument_id']))
            return stocks
        except Exception:
            raise APIError('Unable to find similar stocks')

    def get_news(self):
        """Get news for this stock"""
        try:
            res = self.session.get(ENDPOINTS['news'] + self.symbol + '/?')
            res.raise_for_status()
            return res.json()['results']
        except Exception:
            raise APIError('Unable to find news')

    @property
    def ratings(self):
        """Get the overall buy/sell/hold ratings for this stock"""
        try:
            res = self.session.get(ENDPOINTS['ratings'] + self.id + '/')
            res.raise_for_status()
            resp_json = res.json()
            summary = dict(
                buy=resp_json['summary']['num_buy_ratings'],
                hold=resp_json['summary']['num_hold_ratings'],
                sell=resp_json['summary']['num_sell_ratings'],
                published=resp_json['ratings_published_at']
            )
            ratings_cnt = summary['buy'] + summary['hold'] + summary['sell']
            summary.update(dict(
                ratings_cnt=ratings_cnt,
                buy_percent=summary['buy'] / ratings_cnt * 100,
                hold_percent=summary['hold'] / ratings_cnt * 100,
                sell_percent=summary['sell'] / ratings_cnt * 100
            ))
            ratings = [
                dict(text=rate_json['text'], rating=rate_json['text'],
                     published=rate_json['published_at'])
                for rate_json in resp_json['ratings']
            ]
            return summary, ratings
        except Exception:
            raise APIError('Unable to access popularity data')

    def __hash__(self):
        return hash(self.type + self.symbol)

    def __eq__(self, other):
        return isinstance(other, Stock) and other.symbol == self.symbol

    def __repr__(self):
        return f'<Stock ({self.simple_name}) [{self.symbol}]>'


class Order:
    """Order object

    Attributes:
        session: (Session) current session used by the API
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
    """

    def __init__(self, session, order_json, asset_type, symbol=None, asset=None, lookup_asset=False):

        self.session = session
        self.json = order_json

        self.id = self.json['id']
        self.side = self.json['side']
        self.time_in_force = self.json['time_in_force']
        self.created_at = self.json['created_at']

        self.quantity = Decimal(self.json['quantity'])
        self.order_type = self.json['type']
        self.asset_type = asset_type
        self.symbol = symbol
        self.asset = asset

        if self.asset_type == 'cryptocurrency':
            self.pair_id = self.json['currency_pair_id']
            self.url = ENDPOINTS['nummus_orders'] + self.id
            if not self.symbol:
                for symbol, asset in Currency.cache.items():
                    if asset.pair_id == self.pair_id:
                        self.symbol = symbol
                        self.asset = asset

        elif self.asset_type == 'stock':
            self.instrument_url = self.json['instrument']
            self.url = ENDPOINTS['orders'] + self.id
            if not self.symbol:
                for symbol, asset in Stock.cache.items():
                    if asset.instrument_url == self.instrument_url:
                        self.symbol = symbol
                        self.asset = asset
                        break
                else:
                    if lookup_asset:
                        self._resolve_asset()

        if 'cancel' in self.json:
            self.cancel_url = self.json['cancel']
        else:
            self.cancel_url = self.json['cancel_url']

        if self.json['price']:
            self.price = Decimal(self.json['price'])
        else:
            self.price = None

        if 'stop_price' in self.json and self.json['stop_price']:
            self.stop_price = Decimal(self.json['stop_price'])
        else:
            self.stop_price = None

    def _resolve_asset(self):
        if self.asset_type == 'stock':
            asset = Stock.from_url(self.session, self.instrument_url)
            self.symbol = asset.symbol
            self.asset = asset

    @property
    def state(self):
        """Get order state [confirmed, queued, cancelled, filled]"""
        try:
            res = self.session.get(self.url)
            res.raise_for_status()
            res_json = res.json()
            return res_json['state']
        except Exception:
            raise APIError('Unable to access order data')

    def cancel(self):
        """Cancel this order"""
        try:
            res = self.session.post(self.cancel_url)
            res.raise_for_status()
            return res.json()
        except Exception:
            raise APIError('Unable to cancel')

    def __repr__(self):
        if self.symbol:
            return f'<Order ({self.id[:8]}) [{self.symbol}]>'
        else:
            # symbol has yet to be identified
            return f'<Order ({self.id[:8]}) [...]>'
