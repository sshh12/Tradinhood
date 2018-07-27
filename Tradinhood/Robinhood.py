import requests
from decimal import getcontext, Decimal

getcontext().prec = 18

ENDPOINTS = {
    'tokin': 'https://api.robinhood.com/oauth2/token/',
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

    def login(self, username='', password=''):

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
            res = self.session.post(ENDPOINTS['tokin'], json=req_json)
            res.raise_for_status()
            res_json = res.json()
        except:
            raise Exception('Login Failed')

        if 'access_token' in res_json:

            self.token = res_json['access_token']
            self.session.headers['Authorization'] = 'Bearer ' + self.token
            return True

        return False

class Currency:

    def __init__(self, session, asset_json):

        self.session = session
        self.json = asset_json

        self.name = self.json['asset_currency']['name']
        self.code = self.json['asset_currency']['code']
        self.symbol = self.json['symbol']
        self.tradable = (self.json['tradability'] == 'tradable')
        self.type = self.json['asset_currency']['type']
        self.order_id = self.json['id']
        self.asset_id = self.json['asset_currency']['id']

    @property
    def current_quote(self):
        try:
            res = self.session.get(ENDPOINTS['forex_market_quote'] + self.order_id + '/')
            res.raise_for_status()
            return res.json()
        except:
            raise Exception('Unable to access market data')

    @property
    def price(self):
        return Decimal(self.current_quote['mark_price'])


    def __repr__(self):
        return f'Currency<{self.name} [{self.code}]>'
