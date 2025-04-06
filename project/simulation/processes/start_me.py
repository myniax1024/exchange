import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.getcwd())

from engine.match_engine import MatchEngine
from engine.synchronizer import OrderBookSynchronizer
from engine.cancel_fairy import CancelFairy
from network.grpc_server import serve_ME

from client.custom_formatter import LogFactory


async def main():
    INDEX = int(input("provide index: \n"))
    PASSWORD = "password"
    # IP_ADDR = "10.194.137.206"
    IP_ADDR = "127.0.0.1"
    EXCHANGE_ADDR = "127.0.0.1:50050"
    BASE_PORT = 50060 + INDEX

    log_directory = os.getcwd()
    log_name = f"simulation_me_{INDEX}"
    logger = LogFactory(log_name, log_directory).get_logger()

    # Create engine, synchronizer, and cancel fairy
    synchronizer = OrderBookSynchronizer(
        engine_id=f"engine_{INDEX}",
        engine_addr=f"{IP_ADDR}:{BASE_PORT + INDEX}",
    )
    cancel_fairy = CancelFairy(
        engine_id=f"engine_{INDEX}",
        engine_addr=f"{IP_ADDR}:{BASE_PORT + INDEX}",
    )

    engine = MatchEngine(
        engine_id=f"engine_{INDEX}",
        engine_addr=f"{IP_ADDR}:{BASE_PORT + INDEX}",
        synchronizer=synchronizer,
        cancel_fairy=cancel_fairy,
        authentication_key=PASSWORD,
    )

    # Start gRPC server
    try:
        server = await serve_ME(engine, f"{IP_ADDR}:{BASE_PORT + INDEX}")
        logger.info(f"Started server {INDEX} on port {BASE_PORT + INDEX}")
        # add to exchange
        await engine.connect_to_exchange(EXCHANGE_ADDR)
        logger.info(f"server {INDEX} connected to exchange")
    except Exception as e:
        logger.error(f"Failed to start server {INDEX}: {e}")
        raise

    discovery_signal = input("enter input to start discovery\n")
    # discover peers and connect synchronizers and cancel fairies
    await engine.discover_peers(EXCHANGE_ADDR)
    print(
        f"synchronizer {engine.engine_id} peers: {engine.synchronizer.peer_addresses}"
    )
    print(
        f"cancel fairy {engine.engine_id} peers: {engine.cancel_fairy.peer_addresses}"
    )

    # server cleanup
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main())
