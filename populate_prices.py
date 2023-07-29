import config
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import REST, TimeFrame
import sqlite3
from datetime import date
import numpy
import tulipy

connection = sqlite3.connect(config.DB_PATH)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute("""
    SELECT id, symbol, name FROM stock
""")

rows = cursor.fetchall()
symbols = [row['symbol'] for row in rows]

stock_dict = {}
for row in rows:
    symbol = row['symbol']
    stock_dict[symbol] = row['id']

api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.BASE_URL)
today = date.today().isoformat()
chunck_size = 200
for i in range(0, 10800, chunck_size):
    symbol_chunk = symbols[i:i+chunck_size]
    barsets = api.get_bars(symbol_chunk, TimeFrame.Day, '2023-04-01')._raw
    print(barsets)
    for bar in barsets:
        symbol = bar['S']
        stock_id = stock_dict[bar['S']]
        recent_closes = [b['c'] for b in barsets if b['S'] == symbol]
        print(f'Processing symbol {symbol}')

        sma_20, sma_50, rsi_14 = None, None, None
        if len(recent_closes) >= 50 and today == bar['t'][0:10]:
            sma_20 = tulipy.sma(numpy.array(recent_closes), period=20)[-1]
            sma_50 = tulipy.sma(numpy.array(recent_closes), period=50)[-1]
            rsi_14 = tulipy.rsi(numpy.array(recent_closes), period=14)[-1]
        
        print(stock_id, bar['t'][0:10],bar['o'],bar['h'],bar['l'],bar['c'],bar['v'], sma_20, sma_50, rsi_14)
        cursor.execute("""
            INSERT INTO stock_price(stock_id, date, open, high, low, close, volume, sma_20, sma_50, rsi_14) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (stock_id, bar['t'][0:10], bar['o'], bar['h'], bar['l'], bar['c'], bar['v'], sma_20, sma_50, rsi_14))
connection.commit()
#print(barsets)