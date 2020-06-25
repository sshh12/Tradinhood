from datetime import datetime
from decimal import Decimal

import tradinhood.endpoints as URL
from tradinhood.errors import *


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
        assert False
        try:
            res = self.session.get(None +
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
            res = self.session.get(URL.API.forex_quote + self.pair_id + '/')
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
        self.instrument_url = URL.API.instruments + self.id + '/'
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
        return Stock.from_url(session, URL.API.instruments + id_ + '/')

    def history(self, bounds='regular', interval='day', span='year'):
        """Retrieve the price history of this stock"""
        try:
            res = self.session.get(URL.API.historicals +
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
            res = self.session.get(URL.API.quotes + self.symbol + '/')
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
            res = self.session.get(URL.API.earnings +
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
            res = self.session.get(URL.API.fundamentals +
                                   self.id + '/?include_inactive=true')
            res.raise_for_status()
            return res.json()
        except Exception:
            raise APIError('Unable to get fundamentals')

    def get_similar(self):
        """Get similar stocks"""
        try:
            res = self.session.get(URL.Dora.instruments_similar + self.id + '/')
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
            res = self.session.get(URL.API.news + self.symbol + '/?')
            res.raise_for_status()
            return res.json()['results']
        except Exception:
            raise APIError('Unable to find news')

    @property
    def ratings(self):
        """Get the overall buy/sell/hold ratings for this stock"""
        try:
            res = self.session.get(URL.API.ratings + self.id + '/')
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
            self.url = URL.Nummus.orders + self.id
            if not self.symbol:
                for symbol, asset in Currency.cache.items():
                    if asset.pair_id == self.pair_id:
                        self.symbol = symbol
                        self.asset = asset

        elif self.asset_type == 'stock':
            self.instrument_url = self.json['instrument']
            self.url = URL.API.orders + self.id
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
