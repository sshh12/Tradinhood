from Tradinhood import Robinhood

rbh = Robinhood()
#rbh.login()
dogecoin = rbh.currencies['DOGE']
print(dogecoin.price)
