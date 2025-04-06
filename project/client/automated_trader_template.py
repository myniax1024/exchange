from client.client import Client
from common.order import Fill
from typing import List
import asyncio
import random

class AutomatedTrader(Client):

    def __init__(
        self,
        name: str,
        authentication_key: str,
        balance: int = 0,
        positions: dict = {},
        location: tuple = (0, 0),
        symbols: list = [],
        delay_factor: float = 1.0,
        exchange_addr: str = "127.0.0.1:50050",
        me_addr: str = "",
        direct_connect: bool = False,
    ):

        super().__init__(
            name,
            authentication_key,
            balance,
            positions,
            location,
            symbols,
            delay_factor,
            exchange_addr,
            me_addr,
            direct_connect,
        )

    async def run_loop(self):
        while self.running:
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

        await self.get_fills()
        self.fill_running = False
        self.running = False

        await self.cancel_all_orders()

    async def generate_order(self):
        """ Generate an Order"""
        raise NotImplementedError

    async def process_fills(self, fills: List[Fill]):
        """ Process a list of fills. 

        Args:
            fills (List): List of fills, where each fill is of type common.order.Fill
        """
        raise NotImplementedError

async def main():
    autotrader = AutomatedTrader(name='autotrader', authentication_key='password')

    # run client
    await autotrader.run()

    # run client for some time
    await asyncio.sleep(10) # in seconds

    # stop client
    asyncio.create_task(autotrader.stop())

    await asyncio.sleep(1) # give time to log positions
    autotrader.log_positions() # get final positions

if __name__ == "__main__":
    asyncio.run(main())


