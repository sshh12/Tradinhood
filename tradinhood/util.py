from decimal import getcontext, Decimal
import uuid

# The API seems to use 18 digits, so I copied that
getcontext().prec = 18


def to_decimal(val):
    if val is None:
        return None
    return Decimal(val)


def split_rh_order_type(type_):
    order_type = "market" if (type_ in ["market", "stoploss"]) else "limit"
    trigger = "immediate" if (type_ in ["market", "limit"]) else "stop"
    return order_type, trigger


def gen_ref_id():
    return str(uuid.uuid4())
