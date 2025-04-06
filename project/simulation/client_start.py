import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.getcwd())

from simulation.client_examples.random_client import RandomClient
from simulation.client_examples.market_maker import MarketMaker
from client.client import Client


async def main():
    symbol_list = ["AAPL"]
    DELAY_FACTOR = 2
    SIM_DURATION = 10  # in seconds
    EXCHANGE_ADDR = "127.0.0.1:50050"
    random_client_names = [
        "Adam",
        #        "Betsy",
        #        "Charlie",
        #        "Diana",
        #        "Eric",
        #        "Fred",
        #        "Geoffrey",
        #        "Harry",
        #        "Ian",
        #        "Jill",
        #        "Kelly",
        #        "Larry",
        #        "Mike",
        #        "Natalie",
        #        "Oscar",
    ]
    clients = []

    for client_name in random_client_names:
        clients.append(
            RandomClient(
                name=client_name,
            )
        )

    clients.append(
        MarketMaker(
            name='imc'
        )
    )

    for client in clients:
        await client.run()

    await asyncio.sleep(SIM_DURATION)

    for client in clients:
        asyncio.create_task(client.stop())

    await asyncio.sleep(1)  # give time to log positions

    for client in clients:
        client.log_positions()  # get final positions


if __name__ == "__main__":
    asyncio.run(main())
