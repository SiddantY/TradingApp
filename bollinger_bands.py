import sqlite3
import config
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import REST, TimeFrame
from datetime import date, time, datetime
import pytz
import tulipy
from utilities import calculate_quantity

connection = sqlite3.connect(config.DB_PATH)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

cursor.execute("""
    select id from strategy where name = 'bollinger_bands'
""")

strategy_id = cursor.fetchone()['id']

cursor.execute("""
    select symbol, name
    from stock
    join stock_strategy on stock_strategy.stock_id = stock.id
    where stock_strategy.strategy_id = ?
""", (strategy_id, ))

stocks = cursor.fetchall()
symbols = [stock['symbol'] for stock in stocks]
print(symbols)

today = date.today().isoformat()

start_minute_bar = f"{today} 13:30:00+00:00"
end_minute_bar = f"{today} 21:00:00+00:00"

api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, config.BASE_URL)

orders = api.list_orders(status='all', after=f"{today}T8:00:00Z", limit=500)
existing_order_symbols = [order.symbol for order in orders if order.status != 'canceled']

UTC = pytz.timezone('UTC')

for symbol in symbols:
    minute_bars = api.get_bars(symbol, timeframe=TimeFrame.Minute, start=today).df
    open_mask  = (minute_bars.index >= start_minute_bar) & (minute_bars.index < end_minute_bar)
    market_open_bars = minute_bars.loc[open_mask]
    print(market_open_bars)

    if len(market_open_bars) > 20 and datetime.utcnow().time() > time(13,29) and datetime.utcnow().time() < time(21,00):
        if symbol not in existing_order_symbols:
            closes = market_open_bars.close.values
            print(closes)

            lower, middle, upper = tulipy.bbands(closes, 20, 2)

            current_candle = market_open_bars.iloc[-1]
            previous_candle = market_open_bars.iloc[-2]

            if current_candle.close > lower[-1] and previous_candle.close < lower[-2]:
                print(f"{symbol} closed above lower bollinger band")
                limit_price = current_candle.close
                print(f'placing order for {symbol} at {limit_price}')
                api.submit_order(
                    symbol=symbol,
                    side='buy',
                    type='limit' ,
                    qty=calculate_quantity(limit_price),
                    time_in_force='day',
                    order_class='bracket',
                    limit_price=limit_price,
                    take_profit=dict(
                        limit_price=round(limit_price + (current_candle.high - current_candle.close)*3,2)
                    ),
                    stop_loss=dict(
                        stop_price=round(previous_candle.low,2)
                    )
                )


