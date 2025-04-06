import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.getcwd())

from engine.exchange import Exchange
from network.grpc_server import serve_exchange

from client.custom_formatter import LogFactory


async def main():
    PASSWORD = "password"
    EXCHANGE_ADDR = "127.0.0.1:50050"

    log_directory = os.getcwd()
    log_name = "simulation_exchange"
    logger = LogFactory(log_name, log_directory).get_logger()

    # Create Exchange
    # NOTE: Exchange should only have access to the matching engine addresses and locations, and not the matching engines themselves.
    exchange = Exchange(me_data={}, authentication_key=PASSWORD)
    try:
        exchange_server = await serve_exchange(exchange, EXCHANGE_ADDR)
        logger.info(f"Started exchange on address {EXCHANGE_ADDR}")
    except Exception as e:
        logger.error(f"Failed to start exchange: {e}")
        raise

    await exchange_server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main())
