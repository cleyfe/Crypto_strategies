#installed version:
#numpy==1.19.5
#pandas==pandas==0.25.3

import pandas as pd
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
import pyfolio as pf

#import the backtesting routines
import bt
import ffn

#import sqldatabases for data
import sqlalchemy
from sqlalchemy import create_engine

import pprint

#import the strategies from the Python script
from ipynb.fs.full.MA_strategies import SMA, EMA, MOM, Simple_MOM, Low_Vol, BEST_50MA, BEST_50MA_noMLN

#Import the databases computed with the other Python script
engine12h = sqlalchemy.create_engine('sqlite:///CRYPTO_DB_12h.db')
engine1d = sqlalchemy.create_engine('sqlite:///CRYPTO_DB_1d.db')
engine1w = sqlalchemy.create_engine('sqlite:///CRYPTO_DB_1w.db')
engine1M = sqlalchemy.create_engine('sqlite:///CRYPTO_DB_1M.db')

#dynamic selection of the database based on the frequency indicated below
engine = [engine1d, engine12h, engine1w, engine1M]
freq = ['1d','12h','1w','1M']   

#set parameters
frq = '1d'
mom = 7 #momentum period
N = 20 #number of holding in the long and short legs
Max_w = 0.35 #maximum absolute weight per holding
W = 45 #low volatility and SMA window
S = 1 #select 1 if long short, 0 if long only
reverse = 0 #select 1 if you want to inverse the short and the long leg

#import USDT coins from the other Python script
from ipynb.fs.full.Binance_tokens import get_all_USDT_coins
coins = get_all_USDT_coins()
#coins = ('BTCUSDT','ETHUSDT')


#smart contract platforms on Polygon
#coins = ('BTCUSDT','ETHUSDT','LUNAUSDT','MATICUSDT','MLNUSDT')
'''
coins = ('LINKUSDT','VETUSDT','NULSUSDT','ICXUSDT',
        'ETCUSDT','TRXUSDT','ONTUSDT','XLMUSDT',
        'IOTAUSDT','TUSDUSDT','EOSUSDT','XRPUSDT',
        'ADAUSDT','QTUMUSDT','LTCUSDT','NEOUSDT',
        'BNBUSDT','ETHUSDT','BTCUSDT')'''

#assets universe polygon
#coins = ('ETHUSDT', 'BTCUSDT', 'MATICUSDT', 'ADAUSDT', 'LINKUSDT', 'BNBUSDT', 'DOTUSDT', 'QUICKUSDT', 'SANDUSDT', 'UMAUSDT', 'UNIUSDT', '1INCHUSDT', 'ALGOUSDT', 'BATUSDT', 'DOGEUSDT', 'EOSUSDT', 'LTCUSDT', 'LUNAUSDT', 'MANAUSDT', 'MFTUSDT', 'OMGUSDT', 'SNXUSDT', 'SOLUSDT', 'SUSHIUSDT')

#get prices
data = pd.DataFrame()
for coin in coins:
    prices = pd.read_sql(coin, engine[freq.index(frq)]).set_index('Time')
    #allow fractional trading:
    #prices = (prices / 1e6) # μBTC OHLC prices
    #try:
        #prices = prices.drop_duplicates(keep ='last')
    data[coin] = prices['Close']
    #except:
        #data = prices['Close'].to_frame().combine_first(data)
        #data = data.rename(columns={'Close':coin})        

data = data[-109:].dropna(axis=1, thresh=109)
#data = data.dropna(axis=0)


# create the strategy
#algo = SMA(data, W, S, Max_w)
#algo = EMA(data, S, Max_w)
#algo = MOM(data, S, mom, N, Max_w)
#algo = Simple_MOM(data)
algo = Low_Vol(data, S, W, N, Max_w, reverse)
#algo = BEST_50MA(data)

#bkweights = {'ETHUSDT':1}

bkweights = {'BTCUSDT': 0.5,
             'ETHUSDT':0.5}



strat = bt.Strategy('Low Volatility', [bt.algos.RunOnDate(*algo.weights.index),
                              algo,
                              bt.algos.Rebalance()])

bench = bt.Strategy('50% BTC, 50% ETH', [bt.algos.RunOnDate(*algo.weights.index),
                              bt.algos.WeighSpecified(**bkweights),
                              bt.algos.Rebalance()])


#set commissions
def commissions(q, p, sell_fee=0.005, buy_fee=0.005):
    sell_position = - q 

    if sell_position: # if position is negative (short/sell)
        fee = q*p*sell_fee #per share pay 0.5%

    else:
        fee = -p*q*buy_fee #per share pay 0.5%

    return fee

# create a backtest and run it
btstrat = bt.Backtest(strat, data, initial_capital = 5000, commissions=commissions, integer_positions=False, progress_bar=True)
btbench = bt.Backtest(bench, data, integer_positions=False, progress_bar=True)
btstrat.run()
btbench.run()

res = bt.backtest.Result(btstrat, btbench)


res.display()

# first let's see an equity curve
res.prices = res.prices[45:]
res.plot().set_yscale('log')

#relative performance
_ = res.prices.apply(lambda x: x[0]/x[1], axis=1).plot(title='relative performance', figsize=(15,5))

# ok and how does the return distribution look like?
res.plot_histogram()

# and just to make sure everything went along as planned, let's plot the security weights over time
#res.plot_security_weights(filter=['BTCUSDT','ETHUSDT'])
res.plot_security_weights()

pf.create_full_tear_sheet(res.get("Buckets Easy Systematic Trading - BEST50").prices.pct_change())
#pf.create_full_tear_sheet(res.get("B&H").prices.pct_change())


#turnover
wchange = algo.weights.diff(1)
turnover = abs(wchange).sum(axis=1)*100
plt.plot(turnover.index, turnover, label = "Turnover")
avg = [np.mean(turnover)]*len(turnover)

plt.plot(turnover.index, avg, label = "Average")
print("Average Turnover: ", avg[-1])
#latest composition:
algo.weights[algo.weights != 0].iloc[-1].dropna()

