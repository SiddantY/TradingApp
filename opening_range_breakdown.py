import sqlite3
import config
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import REST, TimeFrame
from datetime import date, time, datetime
from utilities import calculate_quantity

connection = sqlite3.connect(config.DB_PATH)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()

cursor.execute("""
    select id from strategy where name = 'opening_range_breakdown'
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

api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, config.BASE_URL)

today = date.today().isoformat()

orders = api.list_orders(status='all', after=f"{today}T8:00:00Z", limit=500)
existing_order_symbols = [order.symbol for order in orders if order.status != 'canceled']



start_minute_bar = f"{today} 13:30:00+00:00"
end_minute_bar = f"{today} 14:30:00+00:00"


for symbol in symbols:
    minute_bars = api.get_bars(symbol, timeframe=TimeFrame.Minute, start=today).df
    if len(minute_bars) <= 0:
        continue
    opening_range_mask  = (minute_bars.index >= start_minute_bar) & (minute_bars.index < end_minute_bar)
    opening_range_bars = minute_bars.loc[opening_range_mask]
    opening_range_low = opening_range_bars['low'].min()
    opening_range_high = opening_range_bars['high'].max()
    opening_range = opening_range_high - opening_range_low
    print(symbol)
    print(opening_range_bars)
    print(opening_range)
    print(opening_range_high)
    print(opening_range_low)

    after_opening_range_mask = minute_bars.index >= end_minute_bar
    after_opening_range_bars = minute_bars.loc[after_opening_range_mask]

    print(after_opening_range_bars)

    after_opening_range_breakdown = after_opening_range_bars[after_opening_range_bars['close'] < opening_range_low]
    if not after_opening_range_breakdown.empty:
        if datetime.utcnow().time() > time(13,30) and datetime.utcnow().time() < time(21,00):
            if symbol not in existing_order_symbols:
                print(after_opening_range_breakdown)
                limit_price = after_opening_range_breakdown.iloc[0]['close']
                print(limit_price)
                print(f'placing order for {symbol} at {limit_price}, closed above {opening_range_high}')
                api.submit_order(
                    symbol=symbol,
                    side='sell',
                    type='limit' ,
                    qty=calculate_quantity(limit_price),
                    time_in_force='day',
                    order_class='bracket',
                    limit_price=limit_price,
                    take_profit=dict(
                        limit_price=round(limit_price-opening_range,1)
                    ),
                    stop_loss=dict(
                        stop_price=round(limit_price+opening_range,1)
                    )
                )
            else:
                print(f"You already have an order for {symbol}")

