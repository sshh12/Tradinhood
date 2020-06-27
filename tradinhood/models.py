"""
Robinhood API Objects
"""
from datetime import datetime
from decimal import Decimal

import tradinhood.endpoints as URL
from tradinhood.errors import *
from tradinhood.util import *


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
        self.name = self.json["asset_currency"]["name"]
        self.code = self.json["asset_currency"]["code"]
        self.symbol = self.json["symbol"]
        self.tradable = self.json["tradability"] == "tradable"
        self.type = self.json["asset_currency"]["type"]
        self.pair_id = self.json["id"]
        self.asset_id = self.json["asset_currency"]["id"]
        Currency.cache[self.code] = self

    def history(self, bounds="24_7", interval="day", span="year"):
        """Retrieve the price history of this crypto"""
        return self.rbh._get_authed(
            URL.API.forex_historicals + "{}/?bounds={}&interval={}&span={}".format(self.pair_id, bounds, interval, span)
        )["data_points"]

    @property
    def market_open(self):
        """Is this crypto's market open"""
        return True  # I think its always open...

    @property
    def current_quote(self):
        """Current trade data"""
        return self.rbh._get_authed(URL.API.forex_quote + self.pair_id + "/")

    @property
    def price(self):
        """Current price"""
        return to_decimal(self.current_quote["mark_price"])

    @property
    def ask(self):
        """Current ask price"""
        return to_decimal(self.current_quote["ask_price"])

    @property
    def bid(self):
        """Current bid price"""
        return to_decimal(self.current_quote["bid_price"])

    def __hash__(self):
        return hash(self.type + self.code)

    def __eq__(self, other):
        return isinstance(other, Currency) and other.code == self.code

    def __repr__(self):
        return f"<Currency ({self.name}) [{self.code}]>"


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
        self.id = self.json["id"]
        self.name = self.json["name"]
        self.simple_name = self.json["simple_name"]
        self.symbol = self.json["symbol"]
        self.code = self.symbol
        self.tradable = self.json["tradeable"]
        self.type = self.json["type"]
        self.instrument_url = URL.API.instruments + self.id + "/"
        self.market_url = self.json["market"]
        self.fractional = self.json.get("fractional_tradability") == "tradeable"
        self.chain_id = self.json.get("tradable_chain_id")
        self.bloomberg_id = self.json.get("bloomberg_unique")
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
        return Stock.from_url(rbh, URL.API.instruments + id_ + "/")

    def history(self, bounds="regular", interval="day", span="year"):
        """Retrieve the price history of this stock"""
        try:
            res = self.rbh._get_authed(
                URL.API.historicals + "{}/?bounds={}&interval={}&span={}".format(self.symbol, bounds, interval, span)
            )
            return res["historicals"]
        except Exception:
            raise APIError("Unable to access historical market data")

    @property
    def market_open(self):
        """If the market for this stock is open"""
        return self.rbh._get_authed(self.market_url + "hours/" + datetime.today().isoformat()[:10] + "/")["is_open"]

    @property
    def current_quote(self):
        """Stock quote info"""
        return self.rbh._get_authed(URL.API.quotes + self.symbol + "/")

    @property
    def price(self):
        """Current price"""
        return to_decimal(self.current_quote["last_trade_price"])

    @property
    def ask(self):
        """Current ask price"""
        return to_decimal(self.current_quote["ask_price"])

    @property
    def bid(self):
        """Current bid price"""
        return to_decimal(self.current_quote["bid_price"])

    @property
    def popularity(self):
        """Get the number of open positions by Robinhood users"""
        pop = self.rbh._get_authed(self.instrument_url + "popularity/")["num_open_positions"]
        return to_decimal(pop)

    @property
    def earnings(self):
        """Get the earnings history and estimates"""
        results = self.rbh._get_pagination(URL.API.earnings + "?instrument=/instruments/" + self.id + "/", pages=3)
        earnings = []
        for item in results:
            earning = {}
            for key in ["year", "quarter", "eps", "report", "call"]:
                earning[key] = item[key]
            earnings.append(earning)
        return earnings

    @property
    def fundamentals(self):
        """Get stock fundamentals"""
        return self.rbh._get_authed(URL.API.fundamentals + self.id + "/?include_inactive=true")

    @property
    def calls(self):
        return self.query_options(type_="call")

    @property
    def puts(self):
        return self.query_options(type_="put")

    def query_options(self, state="active", expiration_dates=None, type_=None, pages=1):
        """Get options for this stock

        Args:
            state: {'active', None}
            expiration_dates: (str) ex. '2020-06-26'
            type_: {'put', 'call', None}
            pages: (int) max pages of options to pull

        Returns:
            (list<Option>) Options found
        """
        assert self.chain_id is not None
        url = URL.API.options + "?chain_id={}".format(self.chain_id)
        if state is not None:
            url += f"&state={state}"
        if type_ is not None:
            url += f"&type={type_}"
        if expiration_dates is not None:
            url += f"&expiration_dates={expiration_dates}"
        results = self.rbh._get_pagination(url, pages=pages)
        return [Option.from_json(self.rbh, self, result) for result in results]

    def get_similar(self):
        """Get similar stocks"""
        results = self.rbh._get_authed(URL.Dora.instruments_similar + self.id + "/")["similar"]
        stocks = []
        for item in results:
            stocks.append(Stock.from_id(self.rbh, item["instrument_id"]))
        return stocks

    def get_news(self, pages=1):
        """Get news for this stock"""
        return self.rbh._get_pagination(URL.API.news + self.symbol + "/?", pages=pages)

    @property
    def ratings(self):
        """Get the overall buy/sell/hold ratings for this stock"""
        resp_json = self.rbh._get_authed(URL.API.ratings + self.id + "/")
        summary = dict(
            buy=resp_json["summary"]["num_buy_ratings"],
            hold=resp_json["summary"]["num_hold_ratings"],
            sell=resp_json["summary"]["num_sell_ratings"],
            published=resp_json["ratings_published_at"],
        )
        ratings_cnt = summary["buy"] + summary["hold"] + summary["sell"]
        summary.update(
            dict(
                ratings_cnt=ratings_cnt,
                buy_percent=summary["buy"] / ratings_cnt * 100,
                hold_percent=summary["hold"] / ratings_cnt * 100,
                sell_percent=summary["sell"] / ratings_cnt * 100,
            )
        )
        ratings = [
            dict(text=rate_json["text"], rating=rate_json["text"], published=rate_json["published_at"])
            for rate_json in resp_json["ratings"]
        ]
        return summary, ratings

    def __hash__(self):
        return hash(self.type + self.symbol)

    def __eq__(self, other):
        return isinstance(other, Stock) and other.symbol == self.symbol

    def __repr__(self):
        return f"<Stock ({self.simple_name}) [{self.symbol}]>"


class Order:
    """Order object

    Attributes:
        json: (dict) internal data json
        id: (str) the order id
        ref_id: (str) the order ref id
        side: (str) {'sell', 'buy'}
        time_in_force: (str) how the order in enforced
        created_at: (str) when the order was created
        quantity: (Decimal) quantity of the asset
        asset_type: (str) {'cryptocurrency', 'stock'}
        order_type: (str) order type, ex. 'market'
        extended_hours: (bool) if this was an extended hours order
        average_price: (Decimal) the avg price of a stock in the order
        cumulative_quantity: (Decimal) the cumulative amt of stock
        price: (Decimal) order price (or None)
        stop_price: (Decimal) the stop price (or None)
        transaction_at: (str) timestamp of the latest transaction
        asset: (Stock or Currency) the asset traded in the order, defaults None
    """

    def __init__(self, rbh, order_json, asset_type, asset=None, lookup_asset=False):
        self.rbh = rbh
        self.json = order_json
        self.id = self.json["id"]
        self.ref_id = self.json["ref_id"]
        self.side = self.json["side"]
        self.time_in_force = self.json["time_in_force"]
        self.created_at = self.json["created_at"]
        self.quantity = to_decimal(self.json["quantity"])
        self.order_type = self.json["type"]
        self.extended_hours = self.json.get("extended_hours", False)
        self.average_price = to_decimal(self.json.get("average_price"))
        self.cumulative_quantity = to_decimal(self.json.get("cumulative_quantity"))
        self.transaction_at = self.json["last_transaction_at"]
        self.asset_type = asset_type
        self.asset = asset
        if self.asset_type == "cryptocurrency":
            self.pair_id = self.json["currency_pair_id"]
            self.url = URL.Nummus.orders + self.id
            for symbol, asset in Currency.cache.items():
                if asset.pair_id == self.pair_id:
                    self.asset = asset
                    break
        elif self.asset_type == "stock":
            self.instrument_url = self.json["instrument"]
            self.url = URL.API.orders + self.id
            for symbol, asset in Stock.cache.items():
                if asset.instrument_url == self.instrument_url:
                    self.asset = asset
                    break
            else:
                if lookup_asset:
                    self._resolve_asset()
        if "cancel" in self.json:
            self.cancel_url = self.json["cancel"]
        else:
            self.cancel_url = self.json["cancel_url"]
        self.price = to_decimal(self.json.get("price"))
        self.stop_price = to_decimal(self.json.get("stop_price"))

    def _resolve_asset(self):
        if self.asset_type == "stock":
            self.asset = Stock.from_url(self.rbh, self.instrument_url)
        else:
            raise NotImplementedError()

    @property
    def details(self):
        """Fetch up-to-date info about this order"""
        return self.rbh._get_authed(self.url)

    @property
    def state(self):
        """Get order state [confirmed, queued, cancelled, filled]"""
        return self.details["state"]

    def cancel(self):
        """Cancel this order"""
        return self.rbh._post_authed(self.cancel_url)

    def __repr__(self):
        if self.asset is not None:
            return f"<Order ({self.id[:8]}) [{self.asset.symbol}]>"
        else:
            # symbol has yet to be identified
            return f"<Order ({self.id[:8]}) [...]>"


class OptionsOrder:
    """Options Order object

    Attributes:
        json: (dict) internal data json
        id: (string) robinhood id
        direction: (string) the order direct, ex. debit
        ref_id: (str) the order ref id
        created_at: (str) when the order was created
        assets: (list<Option>) the options in this order
        price: (Decimal) order price (or None)
        stop_price: (Decimal) the stop price (or None)
        premium: (Decimal) the cost of this order
        processed_premium: (Decimal) actual cost of this order (ie avg price)
        processed_quantity: (Decimal) quantity processed
    """

    def __init__(self, rbh, order_json, assets=None, lookup_assets=False):
        self.rbh = rbh
        self.json = order_json
        self.id = self.json["id"]
        self.ref_id = self.json["ref_id"]
        self.direction = self.json["direction"]
        self.created_at = self.json["created_at"]
        self.cancel_url = self.json["cancel_url"]
        self.url = URL.API.options_orders + self.id
        self.assets = assets
        self.price = to_decimal(self.json.get("price"))
        self.stop_price = to_decimal(self.json.get("stop_price"))
        self.premium = to_decimal(self.json.get("premium"))
        self.processed_premium = to_decimal(self.json.get("processed_premium"))
        self.processed_quantity = to_decimal(self.json.get("processed_quantity"))
        if (assets is None or len(assets) == 0) and lookup_assets:
            self._resolve_assets()

    @property
    def state(self):
        """Get order state [confirmed, queued, cancelled, filled]"""
        return self.rbh._get_authed(self.url)["state"]

    def cancel(self):
        """Cancel this order"""
        return self.rbh._post_authed(self.cancel_url)

    def _resolve_assets(self):
        option_urls = [option_json["option"] for option_json in self.json["legs"]]
        self.assets = [Option.from_url(self.rbh, url) for url in option_urls]

    def __repr__(self):
        if self.assets is not None:
            return f"<OptionsOrder ({self.id[:8]}) [{','.join([repr(asset) for asset in self.assets])}]>"
        else:
            # symbol has yet to be identified
            return f"<OptionsOrder ({self.id[:8]}) [...]>"


class Option:
    """Option object

    Attributes:
        json: (dict) internal data json
        asset: (Stock) stock this option is for
        chain_id: (str) robinhood chain id
        type_: (str) {'call', 'put'}
        strike: (Decimal) strike price
        tradable: (bool) can be traded
    """

    cache = {}

    def __init__(self, rbh, asset, option_json):
        self.rbh = rbh
        self.asset = asset
        self.json = option_json
        self.chain_id = self.json["chain_id"]
        self.type_ = self.json["type"]
        self.strike = to_decimal(self.json["strike_price"])
        self.tradable = self.json["tradability"] == "tradable"
        self.url = self.json["url"]
        Option.cache[self.url] = self

    @staticmethod
    def from_url(rbh, url):
        json_data = rbh._get_authed(url)
        asset = rbh[json_data["chain_symbol"]]
        return Option.from_json(rbh, asset, json_data)

    @staticmethod
    def from_json(rbh, asset, json):
        """Create a option from its json value"""
        for url, option in Option.cache.items():
            if option.url == json["url"]:
                return option
        return Option(rbh, asset, json)

    @property
    def stats(self):
        """Get the price and other info about this option"""
        return self.rbh.get_bulk_options_stats([self])[self]

    @property
    def greeks(self):
        """Get the greeks for this option"""
        stats = self.stats
        greeks = {}
        for greek_letter in ["delta", "gamma", "theta", "rho", "vega"]:
            if stats[greek_letter] is not None:
                greeks[greek_letter] = to_decimal(stats[greek_letter])
        return greeks

    @property
    def ask(self):
        """Current ask price"""
        return to_decimal(self.stats["ask_price"])

    @property
    def bid(self):
        """Current bid price"""
        return to_decimal(self.stats["bid_price"])

    @property
    def price(self):
        """Current price"""
        stats = self.stats
        if stats.get("last_trade_price") is not None:
            return to_decimal(stats["last_trade_price"])
        return None

    @property
    def iv(self):
        """Current implied volatility"""
        return to_decimal(self.stats["implied_volatility"])

    @property
    def volume(self):
        """Current volume"""
        return to_decimal(self.stats["volume"])

    @property
    def open_interest(self):
        """Current open interest"""
        return to_decimal(self.stats["open_interest"])

    def __repr__(self):
        return f"<Option {self.type_.upper()} @ {self.strike} for {self.asset}>"

    def __hash__(self):
        return hash(self.url)

