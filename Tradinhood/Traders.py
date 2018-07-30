import time

class BaseTrader:

    def __init__(self):
        pass

    def start(self):
        pass

    ### ALGO Code ###

    def setup(self):
        pass

    def loop(self):
        pass

    ### ALGO Code ###

class Backtester(BaseTrader):

    def start(self):

        self.setup()

        while True:
            self.loop()

class Robinhood(BaseTrader):

    def start(self):

        self.setup()

        while True:
            time.sleep(60)
            self.loop()
