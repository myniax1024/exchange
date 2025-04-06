from common.order import Fill, pretty_print_OrderRequest
import asyncio
from typing import List
import os
import grpc
import proto.matching_service_pb2 as pb2
import proto.matching_service_pb2_grpc as pb2_grpc

from client.custom_formatter import LogFactory


class CancelFairy:
    def __init__(self, engine_id, engine_addr, peer_addresses=[]):
        self.engine_id = engine_id
        self.engine_addr = engine_addr
        self.peer_addresses = peer_addresses
        # for cancellation
        self.active_orders = {}  # order_id : {remaining_quantity : <int>, address: <str>, order_record : <Order>}
        self.log_directory = os.getcwd() + "/logs/cancelfairy_logs/"
        self.logger = LogFactory(
            f"CancelFairy for ME {self.engine_id}", self.log_directory
        ).get_logger()

        self.stubs = {}

    async def connect_to_peers(self):
        for address in self.peer_addresses:
            try:
                channel = grpc.aio.insecure_channel(address)
                self.stubs.update({address: pb2_grpc.MatchingServiceStub(channel)})
                self.logger.info(f"connected to ME at address: {address}")
            except Exception as e:
                self.logger.error(f"Failed to connect to peer at {address}: {e}")

    async def cancel(self, order_msg, orderbooks):
        """Cancel the order on local ME if found. Otherwise, find on routed ME."""

        self.logger.info(
            f"received cancel request for order {pretty_print_OrderRequest(order_msg)}"
        )
        self.logger.debug(f"received cancel request for full order {order_msg}")
        self.logger.debug(f"stubs: {self.stubs}")

        order_obj = {
            "order_id": order_msg.order_id,
            "symbol": order_msg.symbol,
            "side": order_msg.side,
            "price": order_msg.price,
            "quantity": order_msg.quantity,
            "remaining_quantity": order_msg.quantity,
            "client_id": order_msg.client_id,
            "engine_origin_addr": order_msg.engine_origin_addr,
            "timestamp": order_msg.timestamp,
        }

        self.logger.debug(f"active_orders: {self.active_orders}")

        async with asyncio.Lock():
            if order_msg.order_id in self.active_orders.keys():
                if (
                    self.engine_addr
                    != self.active_orders[order_msg.order_id]["address"]
                ):
                    self.logger.info(
                        f"Routing cancel request to ME {self.active_orders[order_msg.order_id]['address']}"
                    )
                    response = await self.stubs[
                        self.active_orders[order_msg.order_id]["address"]
                    ].CancelOrder(
                        pb2.CancelOrderRequest(
                            order_id=order_msg.order_id,
                            client_id=order_msg.client_id,
                            order_record=order_obj,
                        )
                    )

                    return_val = True if response.status == "SUCCESSFUL" else False
                    if return_val:
                        self.logger.info("Remotely handled cancel was successful")
                    return return_val, response.quantity_cancelled
                else:
                    self.logger.info("Cancel being handled on local engine")
                    cancel_result = await orderbooks[order_msg.symbol].cancel_order(
                        order_msg, self.active_orders, self.logger
                    )

                    self.logger.debug(f"cancel called on orderbook {order_msg.symbol}")
                    try:
                        del self.active_orders[order_msg.order_id]
                    except Exception as e:
                        self.logger.warning(
                            f"cancel had status {cancel_result} on orderbook but was not found in the active_orders table\nclient may have attempted to cancel a fully filled order. \n Error message {e}"
                        )

                    if cancel_result[0]:
                        self.logger.info("Locally handled cancel was successful")
                    return cancel_result

            else:
                self.logger.warning(
                    f"cancel for {order_msg} did not have an id in active orders"
                )
                return False, 0

    async def update_active_orders_after_fills(self, fills: List[tuple[str, Fill]]):
        self.logger.info(f"updating active orders with {len(fills)} fills")
        self.logger.debug(f"updating active orders with fills {fills}")
        async with asyncio.Lock():
            for fill in fills:
                self.logger.debug(f"update active order with specific fill {fill}")
                if fill[1].order_id in self.active_orders.keys():
                    self.active_orders[fill[1].order_id]["remaining_quantity"] = fill[
                        1
                    ].remaining_quantity

                    if self.active_orders[fill[1].order_id]["remaining_quantity"] <= 0:
                        try:
                            del self.active_orders[fill[1].order_id]
                        except Exception as e:
                            self.logger.warning(
                                f"cancel key was not found on fills\nclient may have attempted to cancel a fully filled order \n Error message {e}"
                            )
