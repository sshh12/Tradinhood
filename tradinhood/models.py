from datetime import datetime
from decimal import Decimal

import tradinhood.endpoints as URL
from tradinhood.errors import *


class Currency:
    """Currency asset object

    Attributes:
        json: (dict) internal data json
        name: (str) currency name
        code: (str) currency symbol
        tradable: (bool) if tradable
        type: (str) asset type
        pair_id: (str) currency Pair id
        asset_id: (str) the APIs id for this currency
    """
    cache = {}

    def __init__(self, rbh, asset_json):
        self.rbh = rbh
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
        return self.rbh._get_authed(URL.API.forex_historicals + '{}/?bounds={}&interval={}&span={}'.format(self.pair_id, bounds, interval, span))['data_points']

    @property
    def market_open(self):
        """Is this crypto's market open"""
        return True  # I think its always open...

    @property
    def current_quote(self):
        """Current trade data"""
        return self.rbh._get_authed(URL.API.forex_quote + self.pair_id + '/')

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
    """
    cache = {}

    def __init__(self, rbh, instrument_json):
        self.rbh = rbh
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
        self.fractional = (self.json.get('fractional_tradability') == 'tradeable')
        self.chain_id = self.json.get('chain_id')
        self.bloomberg_id = self.json.get('bloomberg_unique')
        Stock.cache[self.symbol] = self

    @staticmethod
    def from_url(rbh, instrument_url):
        """Create a stock from its instrument url"""
        for symbol, stock in Stock.cache.items():  # try cache
            if stock.id in instrument_url:
                return stock
        return Stock(rbh, rbh._get_authed(instrument_url))

    @staticmethod
    def from_id(rbh, id_):
        """Create a stock from its instrument id"""
        return Stock.from_url(rbh, URL.API.instruments + id_ + '/')

    def history(self, bounds='regular', interval='day', span='year'):
        """Retrieve the price history of this stock"""
        try:
            res = self.rbh._get_authed(URL.API.historicals +
                                       '{}/?bounds={}&interval={}&span={}'.format(self.symbol, bounds, interval, span))
            return res['historicals']
        except Exception:
            raise APIError('Unable to access historical market data')

    @property
    def market_open(self):
        """If the market for this stock is open"""
        return self.rbh._get_authed(self.market_url + 'hours/' + datetime.today().isoformat()[:10] + '/')['is_open']

    @property
    def current_quote(self):
        """Stock quote info"""
        return self.rbh._get_authed(URL.API.quotes + self.symbol + '/')

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
        pop = self.rbh._get_authed(self.instrument_url + 'popularity/')['num_open_positions']
        return Decimal(pop)

    @property
    def earnings(self):
        """Get the earnings history and estimates"""
        results = self.rbh._get_pagination(URL.API.earnings +
                                           '?instrument=/instruments/' + self.id + '/', pages=3)
        earnings = []
        for item in results:
            earning = {}
            for key in ['year', 'quarter', 'eps', 'report', 'call']:
                earning[key] = item[key]
            earnings.append(earning)
        return earnings

    @property
    def fundamentals(self):
        """Get stock fundamentals"""
        return self.rbh._get_authed(URL.API.fundamentals +
                                    self.id + '/?include_inactive=true')

    def get_similar(self):
        """Get similar stocks"""
        results = self.rbh._get_authed(URL.Dora.instruments_similar + self.id + '/')['similar']
        stocks = []
        for item in results:
            stocks.append(Stock.from_id(
                self.rbh, item['instrument_id']))
        return stocks

    def get_news(self, pages=1):
        """Get news for this stock"""
        return self.rbh._get_pagination(URL.API.news + self.symbol + '/?', pages=pages)

    @property
    def ratings(self):
        """Get the overall buy/sell/hold ratings for this stock"""
        resp_json = self.rbh._get_authed(URL.API.ratings + self.id + '/')
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

    def __hash__(self):
        return hash(self.type + self.symbol)

    def __eq__(self, other):
        return isinstance(other, Stock) and other.symbol == self.symbol

    def __repr__(self):
        return f'<Stock ({self.simple_name}) [{self.symbol}]>'


class Order:
    """Order object

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
    """

    def __init__(self, rbh, order_json, asset_type, symbol=None, asset=None, lookup_asset=False):
        self.rbh = rbh
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
            asset = Stock.from_url(self.rbh, self.instrument_url)
            self.symbol = asset.symbol
            self.asset = asset
        else:
            raise NotImplementedError()

    @property
    def state(self):
        """Get order state [confirmed, queued, cancelled, filled]"""
        return self.rbh._get_authed(self.url)['state']

    def cancel(self):
        """Cancel this order"""
        return self.rbh._post_authed(self.cancel_url)

    def __repr__(self):
        if self.symbol:
            return f'<Order ({self.id[:8]}) [{self.symbol}]>'
        else:
            # symbol has yet to be identified
            return f'<Order ({self.id[:8]}) [...]>'
