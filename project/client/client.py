import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import random
from datetime import datetime as dt
import pytz
from typing import List
import time
import uuid

from client.custom_formatter import LogFactory
from common.order import (
    Order,
    Side,
    OrderStatus,
    Fill,
    pretty_print_FillResponse,
    pretty_print_OrderRequest,
)

import grpc

import proto.matching_service_pb2 as pb2
import proto.matching_service_pb2_grpc as pb2_grpc


class Client:
    """gRPC client for order submission"""

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
        self.name = name
        self.authentication_key = authentication_key
        self.log_directory = os.getcwd() + "/logs/client_logs/"
        self.log_file = os.getcwd() + "/logs/client_logs/" + name
        self.balance = balance
        self.symbols = symbols
        self.positions = positions.copy()
        for symbol in self.symbols:
            self.positions.update({symbol : 0})
        self.location = location
        self.connected_engine = None
        self.latencies = []
        self.symbols = symbols
        self.delay_factor = delay_factor
        self.exchange_addr = exchange_addr
        self.me_addr = me_addr
        self.connected_to_me = False
        self.direct_connect = direct_connect
        self.active_orders = []

        self.running = False
        self.order_running = False
        self.fill_running = False

        self.logger = LogFactory(self.name, self.log_directory).get_logger()


    async def submit_order(self, order: Order):
        if not self.connected_to_me:
            self.logger.error("No matching engine recorded, order rejected")
        else:
            self.active_orders.append(order)
            send_time = time.time()
            # self.logger.info(f"{self.name} submitted order with ID: {order.order_id} at time {send_time}")
            self.logger.info(f"{self.name}: {order.pretty_print()}")

            eastern = pytz.timezone("US/Eastern")
            order_msg = pb2.OrderRequest(
                order_id=str(order.order_id),
                symbol=str(order.symbol),
                side=str(order.side.name),
                price=float(order.price),
                quantity=int(order.quantity),
                remaining_quantity=int(order.quantity),
                client_id=str(order.client_id),
                engine_origin_addr=str(self.me_addr),
                timestamp=(
                    int(order.timestamp.astimezone(eastern).timestamp() * 10**9)
                ),
            )
            self.logger.debug(f"Sent OrderRequest: {order_msg}")
            response = await self.stub.SubmitOrder(order_msg)

            if response.status == "ERROR":
                self.logger.error(
                    f"Received response to order {order.pretty_print()}: {response.status} {response.error_message}"
                )

            receive_time = time.time()
            self.latencies.append(receive_time - send_time)

    async def get_fills(self):
        fills = []
        if not self.connected_to_me:
            self.logger.error("No matching engine recorded")
        else:
            fill_stream = self.stub.GetFills(
                pb2.FillRequest(
                    client_id=self.name,
                    engine_destination_addr=self.me_addr,  # NOTE: Unused
                    timeout=1_000,  # NOTE: Unused
                )
            )

            fill = await fill_stream.read()
            while fill:
                fills.append(fill)
                self.logger.info(f"FILLED: {pretty_print_FillResponse(fill)}")
                fill = await fill_stream.read()

        return fills

    async def register(self):
        if not self.direct_connect:
            try:
                self.exchange_channel = grpc.aio.insecure_channel(self.exchange_addr)
                self.connected_to_exchange = True
                self.logger.info(
                    f"connected to exchange at address {self.exchange_addr}"
                )

                self.exchange_stub = pb2_grpc.MatchingServiceStub(self.exchange_channel)
                response = await self.exchange_stub.RegisterClient(
                    pb2.ClientRegistrationRequest(
                        client_id=self.name,
                        client_authentication=self.authentication_key,
                        client_x=0,
                        client_y=0,
                    )
                )
                self.logger.info(
                    f"Received registration response from exchange: {response}"
                )
                self.me_addr = response.match_engine_address
            except Exception as e:
                self.logger.error(f"exchange registration error: {e}")

        try:
            self.me_channel = grpc.aio.insecure_channel(self.me_addr)
            self.stub = pb2_grpc.MatchingServiceStub(self.me_channel)
            response = await self.stub.RegisterClient(
                pb2.ClientRegistrationRequest(
                    client_id=self.name,
                    client_authentication=self.authentication_key,
                    client_x=0,
                    client_y=0,
                )
            )

            self.connected_to_me = True
            return response
        except Exception as e:
            self.logger.error(f"match engine registration error: {e}")

        return None

    async def run(self):
        self.logger.info(f"started runnning {self.name}")
        self.running = True
        self.order_running = True
        self.fill_running = True
        registration_response = await self.register()
        if registration_response:
            if "SUCCESSFUL" in registration_response.status:
                asyncio.create_task(self.run_loop())
            else:
                self.logger.error(
                    f"Registration failed for client {self.name} with response status {registration_response.status}"
                )

    async def run_loop(self):
        while self.running:
            await asyncio.sleep(random.random() * self.delay_factor)
            order = await self.generate_order()
            if self.fill_running:
                await self.get_fills()
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
        raise NotImplementedError

    async def process_fills(self, fills: List[Fill]):
        raise NotImplementedError

    def update_positions(self, fill: Fill):
        if fill.symbol not in self.positions.keys():
            self.positions.update({fill.symbol: 0})
        if fill.buyer_id == self.name:
            self.balance -= fill.quantity * fill.price
            self.positions[fill.symbol] += fill.quantity
        if fill.seller_id == self.name:
            self.balance += fill.quantity * fill.price
            self.positions[fill.symbol] -= fill.quantity

    def log_positions(self, priority: str = "INFO"):
        if priority == "INFO":
            self.logger.info(f"Name: {self.name}")
            self.logger.info(f"Balance: {round(self.balance, 2)}")
            self.logger.info(f"Positions: \n {self.positions}")
        if priority == "DEBUG":
            self.logger.debug(f"Name: {self.name}")
            self.logger.debug(f"Balance: {round(self.balance, 2)}")
            self.logger.debug(f"Positions: \n {self.positions}")

    def mean_latency(self):
        return sum(self.latencies) / len(self.latencies)

    def _generate_random_order(self, symbols: list = []) -> Order:
        """Generate a random order"""

        order_symbols = []
        if symbols:
            order_symbols = symbols
        else:
            order_symbols = self.symbols

        gen_quantity = random.randint(1, 100)

        if gen_quantity % 2 == 0:
            gen_side = Side.SELL
            gen_price = round(random.uniform(90, 110), 2)
        else:
            gen_side = Side.BUY
            gen_price = round(random.uniform(90, 110), 2)

        return Order(
            order_id=str(uuid.uuid4()),
            symbol=random.choice(order_symbols),
            side=gen_side,
            price=gen_price,
            quantity=gen_quantity,
            remaining_quantity=gen_quantity,
            status=OrderStatus.NEW,
            timestamp=dt.now(),
            client_id=self.name,
            engine_origin_addr=self.me_addr,
        )

    async def cancel_order(self, order: Order):
        self.logger.info(f"cancelling order {pretty_print_OrderRequest(order)}")
        self.logger.debug(f"cancelling full order {order}")

        eastern = pytz.timezone("US/Eastern")
        #        order_obj = {
        #            "order_id" : order.order_id,
        #            "symbol" : order.symbol,
        #            "side" : order.side.name,
        #            "price" : order.price,
        #            "quantity" : order.quantity,
        #            "remaining_quantity" : order.remaining_quantity,
        #            "client_id" : order.client_id,
        #            "engine_origin_addr" : order.engine_origin_addr,
        #            'timestamp' : (int(order.timestamp.astimezone(eastern).timestamp() * 10 ** 9)),
        #        }

        order_obj = pb2.OrderRequest(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side.name,
            price=order.price,
            quantity=int(order.quantity),
            remaining_quantity=int(order.remaining_quantity),
            client_id=order.client_id,
            engine_origin_addr=order.engine_origin_addr,
            timestamp=(int(order.timestamp.astimezone(eastern).timestamp() * 10**9)),
        )

        response = await self.stub.CancelOrder(
            pb2.CancelOrderRequest(
                order_id=order.order_id,
                client_id=order.client_id,
                order_record=order_obj,
            )
        )

        if response.status == "SUCCESSFUL":
            self.logger.info(
                f"cancel was successful for quantity {response.quantity_cancelled}"
            )
        else:
            self.logger.warning("cancel failed")

    async def cancel_all_orders(self):
        self.logger.info(f"cancelling all orders ({len(self.active_orders)} orders)")
        for order in self.active_orders:
            await self.cancel_order(order)
            self.active_orders.remove(order)
