import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.getcwd())

from engine.match_engine import MatchEngine
from engine.exchange import Exchange
from engine.synchronizer import OrderBookSynchronizer
from engine.cancel_fairy import CancelFairy
from network.grpc_server import serve_ME, serve_exchange

from client.custom_formatter import LogFactory


async def main():
    NUM_ENGINES = 1
    PASSWORD = "password"
    # IP_ADDR = "10.194.137.206"
    IP_ADDR = "127.0.0.1"
    engines = []
    synchronizers = []
    servers = []
    base_port = 50051

    log_directory = os.getcwd()
    log_name = "simulation"
    logger = LogFactory(log_name, log_directory).get_logger()

    # Record matching engine data so the exchange layer can map clients to matching engines
    me_data = {}

    # Create Exchange
    # NOTE: Exchange should only have access to the matching engine addresses and locations, and not the matching engines themselves.
    exchange = Exchange(me_data=me_data, authentication_key=PASSWORD)
    exchange_address = f"{IP_ADDR}:{base_port - 1}"
    try:
        exchange_server = await serve_exchange(exchange, exchange_address)
        logger.info(f"Started exchange on port {base_port - 1}")
    except Exception as e:
        logger.error(f"Failed to start exchange: {e}")
        raise

    # Create engines and corresponding synchronizers
    for i in range(NUM_ENGINES):
        synchronizer = OrderBookSynchronizer(
            engine_id=f"engine_{i}",
            engine_addr=f"{IP_ADDR}:{base_port + i}",
        )
        cancel_fairy = CancelFairy(
            engine_id=f"engine_{i}",
            engine_addr=f"{IP_ADDR}:{base_port + i}",
        )

        engine = MatchEngine(
            engine_id=f"engine_{i}",
            engine_addr=f"{IP_ADDR}:{base_port + i}",
            synchronizer=synchronizer,
            cancel_fairy=cancel_fairy,
            authentication_key=PASSWORD,
        )
        engines.append(engine)

        # Start gRPC server
        try:
            server = await serve_ME(engine, f"{IP_ADDR}:{base_port + i}")
            servers.append(server)
            logger.info(f"Started server {i} on port {base_port + i}")
            # add to exchange
            await engine.connect_to_exchange(exchange_address)
            logger.info(f"server {i} connected to exchange")
        except Exception as e:
            logger.error(f"Failed to start server {i}: {e}")
            raise

    for engine in engines:
        # discover peers and connect synchronizers and cancel fairies
        await engine.discover_peers(exchange_address)
        print(
            f"synchronizer {engine.engine_id} peers: {engine.synchronizer.peer_addresses}"
        )
        print(
            f"cancel fairy {engine.engine_id} peers: {engine.cancel_fairy.peer_addresses}"
        )

    # server cleanup
    for i, server in enumerate(servers):
        await server.wait_for_termination()

    await exchange_server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main())
