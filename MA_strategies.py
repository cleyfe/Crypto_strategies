class SMA(bt.Algo):
    
    '''
    Precompute strategy weights. Buy cryptos that are above their 50d sma, Sell those that are below.
    The long and short sides are of equal weights. It requires at least 1 long and 1 short, otherwise it is not invested.
    
    Args:
        *data (dates and one column per crypto with close prices)
         S: 1 if short positions are allowed, 0 otherwise
         Max_w: maximum weight per token
    
    Sets:
        *weights
    '''

    def __init__(self, data, window=50, S=1, Max_w=0.2):
        super(SMA, self).__init__()
        
        '''Trading rules'''        
        sma  = data.rolling(window=window,center=False).mean()

        
        '''Portfolio construction'''
        trend = sma.copy() 
        weights = sma.copy()
        Min_w = -Max_w

        #Determine Buys and Sells
        trend[data > sma] = 1
        buys = trend[trend == 1]
        if S:
            trend[data <= sma] = -1
            sells = trend[trend == -1]
        else:
            trend[data <= sma] = 0

        #Determine weights
        long_weights = buys.fillna(0).apply(lambda x: x/max(1/Max_w,sum(x)), axis=1).fillna(0)
        if S:
            short_weights = sells.fillna(0).apply(lambda x: x if sum(x)==0 else (x/min(1/Min_w,sum(x))), axis=1)
            weights = long_weights - short_weights
        else:
            weights = long_weights

        '''#no absolute short exposure
        for row in range(0,len(weights)):
            if round(sum(weights.iloc[row])) < 0:
                weights.iloc[row] = 0'''

        self.weights = weights
        
        
    def __call__(self, target):
        target.temp['weights'] = self.weights.loc[target.now].to_dict()
                
        
        return True
 

class Simple_MOM(bt.Algo):
    
    '''    
    Precompute strategy weights. 
    Simply go long the top 20 performing coins over the past month, Short the worst 20 coins. No other rules.
    Must be ran with daily data
    
    Args:
        *data (dates and one column per coin with close prices)
    
    Sets:
        *weights
    '''

    def __init__(self, data):
        super(Simple_MOM, self).__init__()
        
        returns  = data/data.shift(7) - 1

        #select top/worst 20 coins
        rank = returns.dropna().rank(ascending=False, axis=1)

        trend = rank.copy() 
        weights = rank.copy()
        coinslen = len(data.columns)

        #replace top/worst 20 coins by  1 and -1. 
        trend[rank <= 20] = 1
        buys = trend[trend == 1]
        trend[rank > (coinslen - 20)] = -1
        sells = trend[trend == -1]
        trend[abs(trend) > 1] = 0

        long_weights = buys.fillna(0).apply(lambda x: x/sum(x), axis=1).fillna(0)
        short_weights = sells.fillna(0).apply(lambda x: x if sum(x)==0 else x/sum(x), axis=1)

        weights = long_weights - short_weights
        self.weights = weights
        
        
    def __call__(self, target):
        target.temp['weights'] = self.weights.loc[target.now].to_dict()
                
        
        return True
