class RobinhoodException(Exception):
    """Basic Robinhood exception"""
    pass


class APIError(RobinhoodException):
    """An issue interfacing with the Robinhood API"""
    pass


class UsageError(RobinhoodException):
    """An issue using this interface"""
    pass
