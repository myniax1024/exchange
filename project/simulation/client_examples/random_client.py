import random
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.getcwd())

from client.client import Client
from common.order import Fill
from typing import List

class RandomClient(Client):
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
            self.log_positions(priority="DEBUG")
            await asyncio.sleep(random.random() * self.delay_factor)
            order = await self.generate_order()
            if self.fill_running:
                fills = await self.get_fills()
                await self.process_fills(fills)
            if self.order_running:
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
        return self._generate_random_order()

    async def process_fills(self, fills: List[Fill]):
        """ Process a list of fills. 

        Args:
            fills (List): List of fills, where each fill is of type common.order.Fill
        """

        for fill in fills:
            self.update_positions(fill)

async def main():
    name = str(input("Supply name: \n"))
    random_client = RandomClient(name=name)

    # run client
    await random_client.run()

    # run client for some time
    await asyncio.sleep(5) # in seconds

    # stop client
    await random_client.stop()

    await asyncio.sleep(1) # give time to log positions
    random_client.log_positions() # get final positions

if __name__ == "__main__":
    asyncio.run(main())

