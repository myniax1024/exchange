import random
import uuid
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.getcwd())

from client.client import Client
from common.order import Fill, Order, Side, OrderStatus
from typing import List
from datetime import datetime as dt

class MarketMaker(Client):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            authentication_key="password",
            symbols=["TSLA"],
            delay_factor=0.00,
            exchange_addr="127.0.0.1:50050",
        )


    async def run_loop(self):
        while self.running:
            await asyncio.sleep(random.random() * self.delay_factor)
            self.log_positions(priority="DEBUG")
            order_list = await self.generate_order()
            if self.fill_running:
                fills = await self.get_fills()
                await self.process_fills(fills)
            if self.order_running:
                for order in order_list:
                    await self.submit_order(order)

    async def stop(self):
        self.logger.info("Stopping run")
        self.order_running = False
        self.fill_running = False
        self.running = False

        await self.cancel_all_orders()

        fills = await self.get_fills()
        await self.process_fills(fills)

    async def generate_order(self):
        """ Generate an Order. """
        order_list = []
        for symbol in self.symbols: 
            if (random.random() < 0.5):
                order_list.append(Order(
                    order_id=str(uuid.uuid4()),
                    symbol=symbol,
                    side=Side.BUY,
                    price=99.00,
                    quantity=1,
                    remaining_quantity=10,
                    status=OrderStatus.NEW,
                    timestamp=dt.now(),
                    client_id=self.name,
                    engine_origin_addr=self.me_addr,
                ))
            else: 
                order_list.append(Order(
                    order_id=str(uuid.uuid4()),
                    symbol=symbol,
                    side=Side.SELL,
                    price=101.00,
                    quantity=1,
                    remaining_quantity=10,
                    status=OrderStatus.NEW,
                    timestamp=dt.now(),
                    client_id=self.name,
                    engine_origin_addr=self.me_addr,
                ))

        return order_list 


    async def process_fills(self, fills: List[Fill]):
        """ Process a list of fills. 

        Args:
            fills (List): List of fills, where each fill is of type common.order.Fill
        """

        for fill in fills:
            self.update_positions(fill)

async def main():
    name = str(input("Supply name: \n"))
    market_maker = MarketMaker(name=name)

    # run client
    await market_maker.run()

    # run client for some time
    await asyncio.sleep(30) # in seconds

    # stop client
    await market_maker.stop()

    await asyncio.sleep(1) # give time to log positions
    market_maker.log_positions() # get final positions

if __name__ == "__main__":
    asyncio.run(main())

