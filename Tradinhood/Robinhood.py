import requests
from decimal import getcontext, Decimal
import uuid

getcontext().prec = 18

ENDPOINTS = {
    'token': 'https://api.robinhood.com/oauth2/token/',
    'accounts': 'https://api.robinhood.com/accounts/',
    'instruments': 'https://api.robinhood.com/instruments/',
    'quotes': 'https://api.robinhood.com/quotes/',
    'nummus_accounts': 'https://nummus.robinhood.com/accounts/',
    'nummus_order': 'https://nummus.robinhood.com/orders/',
    'holdings': 'https://nummus.robinhood.com/holdings/',
    'currency_pairs': 'https://nummus.robinhood.com/currency_pairs/',
    'forex_market_quote': 'https://api.robinhood.com/marketdata/forex/quotes/'
}

API_HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
    'Connection': 'keep-alive',
    'X-Robinhood-API-Version': '1.221.0'
}

OAUTH_CLIENT_ID = 'c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS'


class Robinhood:

    token = None
    acc_num = None
    nummus_id = None
    logged_in = False
    currencies = {}

    def __init__(self):

        self.session = requests.session()
        self.session.headers = API_HEADERS
        self._load()

    def _load(self):

        asset_currs = self.session.get(ENDPOINTS['currency_pairs']).json()['results']

        for curr_json in asset_currs:

            currency = Currency(self.session, curr_json)
            self.currencies[currency.code] = currency

    def _load_auth(self, acc_num=None, nummus_id=None):

        assert self.logged_in

        res_json = self.session.get(ENDPOINTS['accounts']).json()['results']
        res_nummus_json = self.session.get(ENDPOINTS['nummus_accounts']).json()['results']

        if not acc_num:
            self.acc_num = res_json[0]['account_number']
        else:
            self.acc_num = acc_num

        if not nummus_id:
            self.nummus_id = res_nummus_json[0]['id']
        else:
            self.nummus_id = nummus_id

    def login(self, username='', password='', token='', acc_num=None, nummus_id=None):

        if token:
            self.token = token
            self.session.headers['Authorization'] = 'Bearer ' + self.token
            self.logged_in = True
            self._load_auth(acc_num)
            return True

        if not username or not password:

            import getpass
            username = input('Username > ')
            password = getpass.getpass('Password > ')

        req_json = {
            'client_id': OAUTH_CLIENT_ID,
            'expires_in': 86400,
            'grant_type': 'password',
            'scope': 'internal',
            'username': username,
            'password': password
        }

        try:
            res = self.session.post(ENDPOINTS['token'], json=req_json)
            res.raise_for_status()
            res_json = res.json()
        except:
            raise Exception('Login failed')

        if 'access_token' in res_json:

            self.token = res_json['access_token']
            self.session.headers['Authorization'] = 'Bearer ' + self.token
            self.logged_in = True
            self._load_auth(acc_num, nummus_id)

            return True

        return False

    def __getitem__(self, symbol):

        if symbol in self.currencies:
            return self.currencies[symbol]

        try:

            assert self.logged_in

            res = self.session.get(ENDPOINTS['instruments'] + '?active_instruments_only=false&symbol=' + symbol)
            res.raise_for_status()
            results = res.json()['results']
            return Stock(self.session, results[0])

        except:
            raise Exception('Unable to find asset')

    def quantity(self, asset, include_held=False):

        assert self.logged_in

        if isinstance(asset, Currency):

            currs = self.holdings

            for curr in currs:

                if curr['currency']['code'] == asset.code:

                    amt = Decimal(curr['quantity_available'])

                    if include_held:
                        amt += Decimal(curr['quantity_held_for_buy'])
                        amt += Decimal(curr['quantity_held_for_sell'])

                    return amt

            return Decimal('0')

        else:
            raise Exception('Invalid asset!')

    def _order(self, order_type, asset, amt, type, price=None):

        assert (order_type == 'buy' or order_type == 'sell')
        assert asset.tradable

        if not price:
            price = asset.price

        price = str(price)
        amt = str(amt)

        if isinstance(asset, Currency):

            assert (type == 'market' or type == 'limit')

            req_json = {
                'type': type,
                'side': order_type,
                'quantity': amt,
                'account_id': self.nummus_id,
                'currency_pair_id': asset.pair_id,
                'price': price,
                'ref_id': str(uuid.uuid4()),
                'time_in_force': 'gtc'
            }

            res = self.session.post(ENDPOINTS['nummus_order'], json=req_json)
            return res.json()

        else:
            raise Exception('Invalid asset')

    def buy(self, asset, amt, type='market', price=None):

        self._order('buy', asset, amt, type, price)

    def sell(self, asset, amt, type='market', price=None):

        self._order('sell', asset, amt, type, price)

    @property
    def account_info(self):

        assert self.logged_in

        try:
            assert self.acc_num != None
            res = self.session.get(ENDPOINTS['accounts'] + self.acc_num)
            res.raise_for_status()
            return res.json()
        except:
            raise Exception('Unable to access account')

    @property
    def holdings(self):

        assert self.logged_in

        try:
            res = self.session.get(ENDPOINTS['holdings'])
            res.raise_for_status()
            return res.json()['results']
        except:
            raise Exception('Unable to access holdings')

    @property
    def withdrawable_cash(self):
        return Decimal(self.account_info['cash_available_for_withdrawal'])

    @property
    def buying_power(self):
        return Decimal(self.account_info['buying_power'])

    @property
    def unsettled_funds(self):
        return Decimal(self.account_info['unsettled_funds'])

class Currency:

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

    @property
    def current_quote(self):
        try:
            res = self.session.get(ENDPOINTS['forex_market_quote'] + self.pair_id + '/')
            res.raise_for_status()
            return res.json()
        except:
            raise Exception('Unable to access currency data')

    @property
    def price(self):
        return Decimal(self.current_quote['mark_price'])

    @property
    def ask(self):
        return Decimal(self.current_quote['ask_price'])

    @property
    def bid(self):
        return Decimal(self.current_quote['bid_price'])

    def __repr__(self):
        return f'Currency<{self.name} [{self.code}]>'

class Stock:

    def __init__(self, session, instrument_json):

        self.session = session
        self.json = instrument_json

        self.id = self.json['id']
        self.name = self.json['name']
        self.simple_name = self.json['simple_name']
        self.symbol = self.json['symbol']
        self.code = self.symbol
        self.tradable = (self.json['tradeable'] == True)
        self.type = self.json['type']

    @property
    def current_quote(self):
        try:
            res = self.session.get(ENDPOINTS['quotes'] + self.symbol + '/')
            res.raise_for_status()
            return res.json()
        except:
            raise Exception('Unable to access stock data')

    @property
    def price(self):
        return Decimal(self.current_quote['last_trade_price'])

    @property
    def ask(self):
        return Decimal(self.current_quote['ask_price'])

    @property
    def bid(self):
        return Decimal(self.current_quote['bid_price'])

    def __repr__(self):
        return f'Stock<{self.simple_name} [{self.symbol}]>'
