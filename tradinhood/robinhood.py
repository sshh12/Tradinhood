from decimal import getcontext, Decimal
from datetime import datetime
import requests
import time
import uuid

import tradinhood.endpoints as URL
from tradinhood.errors import *
from tradinhood.models import *


# The API seems to use 18 digits, so I copied that
getcontext().prec = 18


# jUsT a ChRoMe bRowSer Bro
API_HEADERS = {
    "Accept": "*/*",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Robinhood-API-Version": "1.221.0",
}


# Extracted from Robinhood web app
OAUTH_CLIENT_ID = "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS"


def default_auth_hook(name):
    return input(name + "> ").strip()


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
        asset_currs = self._get_pagination(URL.Nummus.currency_pairs, auth=False)
        for curr_json in asset_currs:
            currency = Currency(self, curr_json)

    def _get_pagination(self, start_url, auth=True, pages=100):
        results = []
        cur_url = start_url
        i = 0
        while cur_url is not None and i < pages:
            if auth:
                resp = self._get_authed(cur_url)
            else:
                resp = self._get_unauthed(cur_url)
            results.extend(resp["results"])
            pages += 1
            cur_url = resp.get("next")
        return results

    def _get_unauthed(self, url):
        try:
            res = self.session.get(url)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            raise APIError("Unable to access endpoint {} (got {})".format(url, e))

    def _get_authed(self, url):
        assert self.logged_in
        try:
            res = self.session.get(url)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            raise APIError("Unable to access endpoint {} (got {})".format(url, e))

    def _post_authed(self, url, params=None):
        try:
            if params is None:
                res = self.session.post(url)
            else:
                res = self.session.post(url, json=params)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            raise APIError("Unable to access endpoint {} (got {})".format(url, e))

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
                res_json = self._get_pagination(URL.API.accounts)
                if len(res_json) == 0:
                    raise APIError(
                        "No robinhood accounts found. " + "You may still be in the process of being verified."
                    )
                self.acc_num = res_json[0]["account_number"]
            else:
                self.acc_num = acc_num
            self.account_url = URL.API.accounts + self.acc_num + "/"
            if not nummus_id:
                res_nummus_json = self._get_pagination(URL.Nummus.accounts)
                if len(res_nummus_json) == 0:
                    raise APIError(
                        "No robinhood crypto accounts found. "
                        + "Try buying some online to get this part of your account activated."
                    )
                self.nummus_id = res_nummus_json[0]["id"]
            else:
                self.nummus_id = nummus_id
        except KeyError:
            raise APIError("Unable to load secure content (retry login)")

    def login(
        self,
        token="",
        username="",
        password="",
        mfa_code="",
        auth_hook=default_auth_hook,
        verification="sms",
        acc_num=None,
        nummus_id=None,
    ):
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
        if token:
            self.token = token
            self.session.headers["Authorization"] = "Bearer " + self.token
            self.logged_in = True
            self._load_auth(acc_num)
            return True

        if not username or not password:
            import getpass

            username = input("Username: ")
            password = getpass.getpass("Password (Hidden): ")

        req_json = {
            "client_id": OAUTH_CLIENT_ID,
            "expires_in": 86400,
            "grant_type": "password",
            "scope": "internal",
            "username": username,
            "password": password,
            "device_token": self.device_token,
            "challenge_type": verification,
        }

        if mfa_code:
            req_json["mfa_code"] = mfa_code

        res_json = {}
        try:
            res = self.session.post(URL.API.token, json=req_json)
            res_json = res.json()
            if "detail" in res_json and "challenge issued" not in res_json["detail"]:
                res.raise_for_status()
        except Exception:
            raise APIError("Login failed " + str(res_json))

        if "detail" in res_json and "challenge issued" in res_json["detail"]:
            code = auth_hook("verification_code")
            challenge_id = res_json["challenge"]["id"]
            challenge_res = self.session.post(URL.API.challenge + challenge_id + "/respond/", json={"response": code})
            if challenge_res.json()["status"] != "validated":
                raise APIError("Provided challenge code failed.")
            self.session.headers["X-ROBINHOOD-CHALLENGE-RESPONSE-ID"] = challenge_id
            try:
                res = self.session.post(URL.API.token, json=req_json)
                res.raise_for_status()
                res_json = res.json()
            except Exception:
                raise APIError("Challenge auth failed")

        if "mfa_required" in res_json and res_json["mfa_required"]:
            mfa_code = auth_hook("mfa_code")
            req_json["mfa_code"] = mfa_code
            try:
                res = self.session.post(URL.API.token, json=req_json)
                res.raise_for_status()
                res_json = res.json()
            except Exception:
                raise APIError("MFA auth failed")

        if "access_token" in res_json:
            self.token = res_json["access_token"]
            self.session.headers["Authorization"] = "Bearer " + self.token
            self.logged_in = True
            self._load_auth(acc_num, nummus_id)
            return True

        return False

    def save_login(self, fn="robinhood-login"):
        """Save login to file"""
        with open(fn, "w") as save_fp:
            save_fp.write(self.token)

    def load_login(self, fn="robinhood-login"):
        """Login from file"""
        with open(fn, "r") as save_fp:
            token = save_fp.read()
        self.login(token=token)

    def __repr__(self):
        return "<Robinhood [Account: {}]>".format(self.acc_num)

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
            results = self._get_pagination(URL.API.instruments + "?active_instruments_only=false&symbol=" + symbol)
            stock = Stock(self, results[0])
            return stock
        except Exception:
            raise APIError("Unable to find asset")

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
        if isinstance(asset, str):
            asset = self.__getitem__(asset)
        if isinstance(asset, Currency):
            assets = self.get_assets(include_positions=False, include_holdings=True, include_held=include_held)
        elif isinstance(asset, Stock):
            assets = self.get_assets(include_positions=True, include_holdings=False, include_held=include_held)
        else:
            raise UsageError("Invalid asset type")
        return assets.get(asset, Decimal("0.00"))

    def _order(
        self,
        order_side,
        asset,
        quantity=1,
        type="market",
        price=None,
        stop_price=None,
        time_in_force="gtc",
        extended_hours=False,
        return_json=False,
    ):
        """Internal order method

        See .buy(...) and .sell(...)
        """
        assert self.logged_in
        assert order_side in ["buy", "sell"]
        assert time_in_force in ["gtc", "gfd", "ioc", "opg"]

        if isinstance(asset, str):
            asset = self.__getitem__(asset)

        assert asset.tradable

        if price is None:
            price = asset.price
        price = str(price)

        ref_id = str(uuid.uuid4())

        if isinstance(asset, Currency):

            assert type in ["market", "limit"]
            assert stop_price is None

            req_json = {
                "type": type,
                "side": order_side,
                "quantity": str(quantity),
                "account_id": self.nummus_id,
                "currency_pair_id": asset.pair_id,
                "price": price,
                "ref_id": ref_id,
                "time_in_force": time_in_force,
            }

            res_json = self._post_authed(URL.Nummus.orders, req_json)

            if "error_code" in res_json:
                raise APIError(res_json["error_code"])

            if return_json:
                return res_json
            else:
                return Order(self, res_json, "cryptocurrency", asset=asset)

        elif isinstance(asset, Stock):

            assert type in ["market", "limit", "stoploss", "stoplimit"]

            # Convert types into correct parameters
            order_type = "market" if (type in ["market", "stoploss"]) else "limit"
            trigger = "immediate" if (type in ["market", "limit"]) else "stop"

            if trigger == "stop":
                assert stop_price
                stop_price = str(stop_price)
            else:
                assert stop_price is None

            req_json = {
                "time_in_force": time_in_force,
                "price": price,
                "quantity": str(round(quantity, 0)),
                "side": order_side,
                "trigger": trigger,
                "type": order_type,
                "account": self.account_url,
                "instrument": asset.instrument_url,
                "symbol": asset.symbol,
                "ref_id": ref_id,
                "extended_hours": extended_hours,
            }

            if stop_price:
                req_json["stop_price"] = stop_price

            res_json = self._post_authed(URL.API.orders, req_json)

            if "error_code" in res_json:
                raise APIError(res_json["error_code"])

            if return_json:
                return res_json
            else:
                return Order(self, res_json, "stock", asset=asset)

        else:
            raise UsageError("Invalid asset")

    def buy(self, asset, **kwargs):
        """Buy item

        Args:
            asset: (Currency | Stock, str) the asset to be bought
            quantity: (Decimal | float | int) the amt to buy
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
        return self._order("buy", asset, **kwargs)

    def sell(self, asset, **kwargs):
        """Sell item

        Args:
            asset: (Currency | Stock | str) tthe asset to be sold
            quantity: (Decimal | float | int) The amt to sell
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
        return self._order("sell", asset, **kwargs)

    def order_options(
        self, legs, quantity=1, price=None, type="limit", direction="debit", time_in_force="gtc", return_json=False
    ):
        """Place an options order

        Args:
            legs: (list<tuples(str, Option, str)>) the order legs
            quantity: (int) amt to buy
            type: (str, optional) the order type
                ['market', 'limit', 'stoploss', 'stoplimit']
            price: (int) price to purchase
            direction: (str) order direction, ex. debit
            time_in_force: (str, optional) when to cancel
                ['gtc', 'gfd', 'ioc', 'opg']

        Returns:
            (Order) the created order
        """
        assert len(legs) > 0
        assert time_in_force in ["gtc", "gfd", "ioc", "opg"]
        if price is None:
            return UsageError("Tbh not sure how to estimate price, for now you have to provide price=?")
        opt_legs = []
        assets = []
        for leg in legs:
            side, option, effect = leg
            assert side in ["buy", "sell"]
            assert effect in ["open", "close"]
            assert isinstance(option, Option)
            assets.append(option)
            opt_legs.append({"side": side, "option": option.url, "position_effect": effect, "ratio_quantity": "1"})
        ref_id = str(uuid.uuid4())
        order_type = "market" if (type in ["market", "stoploss"]) else "limit"
        trigger = "immediate" if (type in ["market", "limit"]) else "stop"
        req_json = {
            "ref_id": ref_id,
            "account": self.account_url,
            "direction": direction,
            "type": order_type,
            "price": str(price),
            "quantity": "todo",
            "override_day_trade_checks": False,
            "override_dtbp_checks": False,
            "time_in_force": time_in_force,
            "trigger": trigger,
            "legs": opt_legs,
            "quantity": str(quantity),
        }
        res_json = self._post_authed(URL.API.options_orders, req_json)
        if "error_code" in res_json:
            raise APIError(res_json["error_code"])
        if return_json:
            return res_json
        else:
            return Order(self, res_json, assets=assets)

    @property
    def orders(self):
        """Get recent order history"""
        return self.query_orders()

    def query_orders(
        self,
        sort_by_time=True,
        include_stocks=True,
        include_crypto=True,
        include_options=True,
        pages=3,
        lookup_assets=True,
    ):
        """Search orders"""
        orders = []
        if include_stocks:
            json_stocks = self._get_pagination(URL.API.orders, pages=pages)
            orders += [Order(self, json_data, "stock", lookup_asset=lookup_assets) for json_data in json_stocks]
        if include_crypto:
            json_crypto = self._get_pagination(URL.Nummus.orders, pages=pages)
            orders += [
                Order(self, json_data, "cryptocurrency", lookup_asset=lookup_assets) for json_data in json_crypto
            ]
        if include_options:
            json_options = self._get_pagination(URL.API.options_orders, pages=pages)
            orders += [OptionsOrder(self, json_data, lookup_assets=lookup_assets) for json_data in json_options]
        if sort_by_time:
            orders.sort(key=lambda o: o.created_at, reverse=True)
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
            return order.state in ["filled", "cancelled"]

        checks = timeout // delay
        while not all(map(order_complete, orders)) and checks > 0:
            time.sleep(delay)
            checks -= 1
        if force:
            for order in orders:
                if order.state in ["confirmed", "queued"]:
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
        my_assets = {}

        if include_positions:
            stocks = self.positions
            for stock_json in stocks:
                stock = Stock.from_url(self, stock_json["instrument"])
                amt = Decimal(stock_json["quantity"])
                if include_held:
                    amt += Decimal(stock_json["shares_held_for_buys"])
                    amt += Decimal(stock_json["shares_held_for_sells"])
                    amt += Decimal(stock_json["shares_held_for_options_collateral"])
                    amt += Decimal(stock_json["shares_held_for_options_events"])
                    amt += Decimal(stock_json["shares_held_for_stock_grants"])
                if include_zero or amt > 0:
                    my_assets[stock] = amt

        if include_holdings:
            currs = self.holdings
            for curr_json in currs:
                code = curr_json["currency"]["code"]
                if code in Currency.cache:  # all currencies already cached
                    curr = Currency.cache[code]
                    amt = Decimal(curr_json["quantity_available"])
                    if include_held:
                        amt += Decimal(curr_json["quantity_held_for_buy"])
                        amt += Decimal(curr_json["quantity_held_for_sell"])
                    if include_zero or amt > 0:
                        my_assets[curr] = amt

        return my_assets

    @property
    def account_info(self):
        """Account info"""
        assert self.acc_num is not None
        return self._get_authed(URL.API.accounts + self.acc_num)

    @property
    def holdings(self):
        """Currency holdings"""
        return self._get_pagination(URL.Nummus.holdings)

    @property
    def positions(self):
        """Share positions"""
        return self._get_pagination(URL.API.positions)

    @property
    def withdrawable_cash(self):
        """Cash that can be withdrawn"""
        return Decimal(self.account_info["cash_available_for_withdrawal"])

    @property
    def buying_power(self):
        """Buying power"""
        return Decimal(self.account_info["buying_power"])

    @property
    def cash(self):
        """Cash"""
        return Decimal(self.account_info["cash"])

    @property
    def unsettled_funds(self):
        """Unsettled funds"""
        return Decimal(self.account_info["unsettled_funds"])

    def get_stocks_by_tag(self, tag):
        """Get stock list by tag

        Args:
            tag: (str) The tag to use (exs. top-movers, 100-most-popular)

        Returns:
            (tuple str, list<Stock>) The name and list of stocks
        """
        resp_json = self._get_authed(URL.API.tags + tag + "/")
        name = resp_json["name"]
        stocks = [Stock.from_url(self, url) for url in resp_json["instruments"]]
        return (name, stocks)

    def history(self, bounds="trading", interval="5minute", span="day", account_id=None):
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
        url = URL.API.portfolios_historicals + "{0}/?account={0}&bounds={1}&interval={2}&span={3}".format(
            account_id, bounds, interval, span
        )
        return self._get_authed(url)

    @property
    def unified_data(self):
        """Get the unified data of the account"""
        return self._get_authed(URL.API.unified)

    @property
    def user_data(self):
        """Get the data about the account user"""
        return self._get_authed(URL.API.user)

    def get_bulk_prices(self, stocks, bounds="trading", include_inactive=True):
        """Get the prices of multiple stocks at the same time

        Args:
            stocks: (list<Stock>) Stocks to find prices for
            bounds: (str) The bounds for the returned price data
            include_inactive: (str) Include inactive stocks

        Returns:
            (dict) Price data
        """
        assert len(stocks) > 0
        instrument_urls = ",".join([stock.instrument_url for stock in stocks])
        url = URL.API.quotes + "?bounds={}&include_inactive={}&instruments={}".format(
            bounds, str(include_inactive).lower(), instrument_urls
        )
        results = self._get_pagination(url)
        prices = {}
        for stock in stocks:
            stock_data = None
            for item in results:
                if item["symbol"] == stock.symbol:
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
        instrument_ids = ",".join([stock.id for stock in stocks])
        url = URL.API.popularity + "?ids={}".format(instrument_ids)
        results = self._get_pagination(url)
        pop = {}
        for item in results:
            item_stock = None
            for stock in stocks:
                if item["instrument"] == stock.instrument_url:
                    item_stock = stock
                    break
            pop[item_stock] = item["num_open_positions"]
        return pop

    def get_bulk_ratings(self, stocks):
        """Get the ratings of multiple stocks at the same time

        Args:
            stocks: (list<Stock>) Stocks to find ratings for

        Returns:
            (dict) Ratings data
        """
        assert len(stocks) > 0
        instrument_ids = ",".join([stock.id for stock in stocks])
        url = URL.API.ratings + "?ids={}".format(instrument_ids)
        results = self._get_pagination(url)
        ratings = {}
        for item in results:
            item_stock = None
            for stock in stocks:
                if item["instrument_id"] == stock.id:
                    item_stock = stock
                    break
            ratings[item_stock] = item["summary"]
        return ratings

    def get_bulk_options_stats(self, options):
        """Get info for multiple options at the same time

        Args:
            options: (list<Option>) Options to find stats for

        Returns:
            (dict) Options data
        """
        assert len(options) > 0
        instrument_urls = ",".join([option.url for option in options])
        url = URL.API.options_marketdata + "?instruments={}".format(instrument_urls)
        results = self._get_pagination(url)
        stats = {}
        for item in results:
            item_option = None
            for option in options:
                if item["instrument"] == option.url:
                    item_option = option
                    break
            stats[item_option] = item
        return stats
