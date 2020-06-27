"""
Tools that are not directly related to the API.
"""
from tradinhood.models import *


def order_profit_loss(rbh, **kwargs):
    """Pair past orders to determine trade profit/loss"""
    # These order query fields must be enabled.
    kwargs["sort_by_time"] = True
    kwargs["state"] = "filled"
    kwargs["lookup_assets"] = True
    orders = rbh.query_orders(**kwargs)
    option_orders = [order for order in orders if isinstance(order, OptionsOrder)]
    crypto_orders = [order for order in orders if isinstance(order, Order) and order.asset_type == "cryptocurrency"]
    stock_orders = [order for order in orders if isinstance(order, Order) and order.asset_type == "stock"]
    pls = []
    pls.extend(_get_stock_profit_loss(stock_orders))
    pls.extend(_get_stock_profit_loss(crypto_orders))
    pls.extend(_get_option_profit_loss(option_orders))
    return pls


def _get_stock_profit_loss(orders):
    order_pool = list(orders)
    pls = []
    while len(order_pool) > 0:
        close_order = None
        open_order = None
        for i, order in enumerate(order_pool):
            if order.side == "sell":
                close_order = order
                break
        if close_order is None:
            break
        for order in order_pool[i + 1 :]:
            if (
                order.side == "buy"
                and order.asset == close_order.asset
                and order.cumulative_quantity == close_order.cumulative_quantity
            ):
                open_order = order
                break
        if open_order is not None:
            open_price = open_order.average_price
            close_price = close_order.average_price
            open_cost = open_order.cumulative_quantity * open_price
            close_cost = close_order.cumulative_quantity * close_price
            pls.append(
                {
                    "open": open_order,
                    "close": close_order,
                    "asset": open_order.asset,
                    "open_price": open_price,
                    "close_price": close_price,
                    "open_cost": open_cost,
                    "close_cost": close_cost,
                    "profit_loss": close_cost - open_cost,
                }
            )
            order_pool.remove(open_order)
        order_pool.remove(close_order)
    return pls


def _get_option_profit_loss(orders):
    # This may be a little broken for adv options trading stuff.
    order_pool = list(orders)
    pls = []
    while len(order_pool) > 0:
        close_order = None
        open_order = None
        for i, order in enumerate(order_pool):
            if order.direction == "credit":
                close_order = order
                break
        if close_order is None:
            break
        for order in order_pool[i + 1 :]:
            if (
                order.direction == "debit"
                and set(order.assets) == set(close_order.assets)
                and order.processed_quantity == close_order.processed_quantity
            ):
                open_order = order
                break
        if open_order is not None:
            open_price = open_order.processed_premium
            close_price = close_order.processed_premium
            open_cost = open_order.processed_quantity * open_price
            close_cost = close_order.processed_quantity * close_price
            pls.append(
                {
                    "open": open_order,
                    "close": close_order,
                    "assets": open_order.assets,
                    "open_price": open_price,
                    "close_price": close_price,
                    "open_cost": open_cost,
                    "close_cost": close_cost,
                    "profit_loss": close_cost - open_cost,
                }
            )
            order_pool.remove(open_order)
        order_pool.remove(close_order)
    return pls
