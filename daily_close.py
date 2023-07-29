import alpaca_trade_api as tradeapi
import config
from datetime import date, time, datetime

now = datetime.now()
current_time = now.strftime("%H:%M:%S")
if current_time >= "16:15:00" and current_time <= "16:59:59":
    api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, config.BASE_URL)

    response = api.close_all_positions()

    print(response)
else:
    print("NO!")