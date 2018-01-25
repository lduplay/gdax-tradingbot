import pandas as pd
import os.path
import matplotlib.pyplot as plt
from exchange import *


class Model(object):
    def __init__(self, csv_prices, csv_transactions):
        # Create CSV files for logging price and transactions
        self.csv_price = csv_prices
        self.csv_transactions = csv_transactions
        #Create dataframes to store data
        self.transaction_dataframe = pd.DataFrame(data={'GDAX_id' : [], 'product_id' : [], 'datetime': [], 'buy/sell': [], 'price': [], 'quantity': [], 'status': []})
        self.ema_dataframe = pd.DataFrame(data={'datetime': [],'price': [], 'EMA5': [], 'EMA20': [], 'signal': []})
        #Add headers to CSV if don't exist
        csv_price_exists = os.path.isfile(self.csv_price)
        csv_transactions_exists = os.path.isfile(self.csv_transactions)
        if not csv_price_exists:          
            self.logPrice(False)
        if not csv_transactions_exists:
            self.logTransactions(False)

    def calculateEma(self, CoinBase, product_id):
        #Get current price and time and add to dataframe
        price = CoinBase.getPrice(product_id)
        datetime = CoinBase.getTime()
        self.ema_dataframe = self.ema_dataframe.append(pd.DataFrame({'datetime': datetime, 'price': price}, index=[0]), ignore_index=True)
        length = self.ema_dataframe.shape[0]
        if length>5:
            self.ema_dataframe['EMA5'] = self.ema_dataframe['price'].dropna().shift().fillna(self.ema_dataframe['EMA5']).ewm(com=5).mean()
        if length>20:
            self.ema_dataframe['EMA20'] = self.ema_dataframe['price'].dropna().shift().fillna(self.ema_dataframe['EMA20']).ewm(com=20).mean()
        self.logPrice(True)

    def calculateCrossover(self):
        #Calculate EMA crossover and return signal
        length = self.ema_dataframe.shape[0]
        if length>5:
            EMA5 = self.ema_dataframe['EMA5'].tail(2).reset_index(drop=True)
            EMA20 = self.ema_dataframe['EMA20'].tail(2).reset_index(drop=True)
            if (EMA5[1] <= EMA20[1]) & (EMA5[0] >= EMA20[0]):
                signal = {'signal': True, 'value': 'sell'}
            elif (EMA5[1] >= EMA20[1]) & (EMA5[0] <= EMA20[0]):
                signal = {'signal': True, 'value': 'buy'}
            else:
                signal = {'signal': False, 'value': None}
            self.ema_dataframe.loc[self.ema_dataframe.index[length-1], 'signal'] = signal['value']
            return signal

    def buy(self, product_id, CoinBase, base_currency):
        #Buy cryptocurrency and return order information
        time = CoinBase.getTime()
        buy_price = float(CoinBase.determinePrice(product_id, 'buy'))
        balance = float(CoinBase.getBalance(base_currency))
        quantity = balance/buy_price
        order = CoinBase.buy(product_id, quantity, buy_price)
        if 'id' in order:
            id = order['id']
            status = order['status']
            self.transaction_dataframe.loc[self.transaction_dataframe.shape[0]] =  [id, product_id, time, 'buy', buy_price, quantity, status]
            self.logTransactions(True)
            return order
        else:
            print(order)
            return -1 

    def sell(self, product_id, CoinBase, quote_currency):
        #Sell cryptocurrency and return order information
        time = CoinBase.getTime()
        sell_price = CoinBase.determinePrice(product_id, 'sell')
        quantity = CoinBase.getAccounts(quote_currency)
        order = CoinBase.sell(product_id, quantity, sell_price, False)
        if 'id' in order:
            id = order['id']
            status = order['status']
            self.transaction_dataframe.loc[self.transaction_dataframe.shape[0]] =  [id, product_id, time, 'sellUpper', sell_price, quantity, status]
            self.logTransactions(True)
            return order
        else:
            print(order)
            return -1 

    def sellUpper(self, product_id, CoinBase, quote_currency, price):
        #Create limit sell order cryptocurrency and return order information
        time = CoinBase.getTime()
        sell_price = float(price) * 1.004 #Limit profit at 0.4%
        quantity = CoinBase.getAccounts(quote_currency)
        order = CoinBase.sell(product_id, quantity, sell_price, True)
        if 'id' in order:
            id = order['id']
            status = order['status']
            self.transaction_dataframe.loc[self.transaction_dataframe.shape[0]] =  [id, product_id, time, 'sell', sell_price, quantity, status]
            self.logTransactions(True)
            return order
        else:
            print(order)
            return -1 

    def plotGraph(self):
        #Plot X/Y graph for both EMAs
        self.ema_dataframe['price'] = self.ema_dataframe['price'].astype(float)
        self.ema_dataframe['EMA5'] = self.ema_dataframe['EMA5'].astype(float)
        self.ema_dataframe['EMA20'] = self.ema_dataframe['EMA20'].astype(float)
        pl = self.ema_dataframe[['datetime', 'price']].plot(label='Price')
        self.ema_dataframe[['datetime', 'EMA5']].plot(label='EMA5', ax=pl)
        self.ema_dataframe[['datetime', 'EMA20']].plot(label='EMA20', ax=pl)
        plt.xlabel('Datetime')
        plt.ylabel('Price')
        plt.legend()
        plt.show()

    def logPrice(self, append):
        #Log price to CSV
        if (append):
            self.ema_dataframe.tail(1).to_csv(self.csv_price, encoding='utf-8', mode='a', index=False, header=False)
        else:
            self.ema_dataframe.tail(1).to_csv(self.csv_price, encoding='utf-8', index=False, header=True)          

    def logTransactions(self, append):
        #Log transactions to CSV
        if (append):
            self.transaction_dataframe.tail(1).to_csv(self.csv_transactions, encoding='utf-8', mode='a', index=False, header=False)
        else:
            self.transaction_dataframe.tail(1).to_csv(self.csv_transactions, encoding='utf-8', index=False, header=True)  