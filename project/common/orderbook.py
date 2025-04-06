from datetime import datetime
from typing import Dict, List
from collections import defaultdict
from .order import Order, Fill


class OrderBook:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids: Dict[float, List[Order]] = defaultdict(list)
        self.asks: Dict[float, List[Order]] = defaultdict(list)

    def __repr__(self):
        """Print state of this order book"""

        rep = ""
        rep += f"\nOrder book for {self.symbol}:"
        rep += "\nAsks:\n"
        for price in sorted(self.asks.keys(), reverse=True):
            if not (sum(o.remaining_quantity for o in self.asks[price]) == 0):
                rep += f"\n\t{price}: {sum(o.remaining_quantity for o in self.asks[price])}"
        rep += "\nBids:\n"
        for price in sorted(self.bids.keys(), reverse=True):
            if not (sum(o.remaining_quantity for o in self.bids[price]) == 0):
                rep += f"\n\t{price}: {sum(o.remaining_quantity for o in self.bids[price])}"

        return rep

    async def cancel_order(self, order_msg, active_orders, logger):
        if order_msg.order_id in active_orders.keys():
            if order_msg.side == "BUY":
                for cancellable_order in self.bids[order_msg.price]:
                    if cancellable_order.order_id == order_msg.order_id:
                        remaining_quantity = cancellable_order.remaining_quantity
                        self.bids[order_msg.price].remove(cancellable_order)
                        logger.info("Successfully cancelled order!")
                        return True, remaining_quantity
            if order_msg.side == "SELL":
                for cancellable_order in self.asks[order_msg.price]:
                    if cancellable_order.order_id == order_msg.order_id:
                        remaining_quantity = cancellable_order.remaining_quantity
                        self.asks[order_msg.price].remove(cancellable_order)
                        logger.info("Successfully cancelled order!")
                        return True, remaining_quantity

            logger.warning("cancel failed: not in orderbook")
            return False, 0
        else:
            logger.warning("cancel failed: not in active_orders")
            return False, 0

    def add_order(self, order: Order, active_orders):
        """Add order to book and return list of fills"""
        fills = {
            "incoming_fills": [],
            "resting_fills": [],
        }
        if order.side == "BUY":
            # Match against asks
            for price in sorted(self.asks.keys()):
                if price > order.price or order.remaining_quantity <= 0:
                    break

                updated_fills = self._match_order_at_price(order, price, active_orders)
                fills["incoming_fills"].extend(updated_fills["incoming_fills"])
                fills["resting_fills"].extend(updated_fills["resting_fills"])
        else:
            # Match against bids
            for price in sorted(self.bids.keys(), reverse=True):
                if price < order.price or order.remaining_quantity <= 0:
                    break
                updated_fills = self._match_order_at_price(order, price, active_orders)
                fills["incoming_fills"].extend(updated_fills["incoming_fills"])
                fills["resting_fills"].extend(updated_fills["resting_fills"])

        # Add remaining quantity to book
        if order.remaining_quantity > 0:
            if order.side == "BUY":
                self.bids[order.price].append(order)
            else:
                self.asks[order.price].append(order)

        return fills

    def _match_order_at_price(
        self, incoming_order: Order, price: float, active_orders
    ) -> Dict[str, list]:
        incoming_fills = []
        resting_fills = []

        if incoming_order.side == "BUY":
            orders = self.asks[price]

            for resting_order in orders[:]:
                if resting_order.order_id in active_orders:
                    fill_qty = min(
                        incoming_order.remaining_quantity,
                        resting_order.remaining_quantity,
                    )
                    if fill_qty <= 0:
                        continue

                    # Update quantities
                    incoming_order.remaining_quantity -= fill_qty
                    resting_order.remaining_quantity -= fill_qty

                    # Create fill records for the incoming order
                    incoming_fills.append(
                        (
                            incoming_order.client_id,
                            Fill(
                                fill_id=f"FILL;incoming:{incoming_order.order_id};resting:{resting_order.order_id}",
                                order_id=incoming_order.order_id,
                                symbol=incoming_order.symbol,
                                side=incoming_order.side,
                                price=price,
                                quantity=fill_qty,
                                remaining_quantity=incoming_order.remaining_quantity,
                                timestamp=datetime.now(),
                                buyer_id=incoming_order.client_id,
                                seller_id=resting_order.client_id,
                                engine_destination_addr=incoming_order.engine_origin_addr,
                            ),
                        )
                    )

                    resting_fills.append(
                        (
                            resting_order.client_id,
                            Fill(
                                fill_id=f"FILL;incoming:{incoming_order.order_id};resting:{resting_order.order_id}",
                                order_id=resting_order.order_id,
                                symbol=resting_order.symbol,
                                side=resting_order.side,
                                price=price,
                                quantity=fill_qty,
                                remaining_quantity=resting_order.remaining_quantity,
                                timestamp=datetime.now(),
                                buyer_id=incoming_order.client_id,
                                seller_id=resting_order.client_id,
                                engine_destination_addr=incoming_order.engine_origin_addr,
                            ),
                        )
                    )

                    # Remove filled orders
                    if resting_order.remaining_quantity <= 0:
                        orders.remove(resting_order)
                        del active_orders[resting_order.order_id]
                    if incoming_order.remaining_quantity <= 0:
                        del active_orders[incoming_order.order_id]
                else:
                    # cancel logic
                    orders.remove(resting_order)

        elif incoming_order.side == "SELL":
            orders = self.bids[price]

            for resting_order in orders[:]:
                if resting_order.order_id in active_orders:
                    fill_qty = min(
                        incoming_order.remaining_quantity,
                        resting_order.remaining_quantity,
                    )
                    if fill_qty <= 0:
                        continue

                    # Update quantities
                    incoming_order.remaining_quantity -= fill_qty
                    resting_order.remaining_quantity -= fill_qty

                    # Create fill records for the incoming order
                    incoming_fills.append(
                        (
                            incoming_order.client_id,
                            Fill(
                                fill_id=f"FILL;incoming:{incoming_order.order_id};resting:{resting_order.order_id}",
                                order_id=incoming_order.order_id,
                                symbol=incoming_order.symbol,
                                side=incoming_order.side,
                                price=price,
                                quantity=fill_qty,
                                remaining_quantity=incoming_order.remaining_quantity,
                                timestamp=datetime.now(),
                                buyer_id=resting_order.client_id,
                                seller_id=incoming_order.client_id,
                                engine_destination_addr=incoming_order.engine_origin_addr,
                            ),
                        )
                    )

                    resting_fills.append(
                        (
                            resting_order.client_id,
                            Fill(
                                fill_id=f"FILL;incoming:{incoming_order.order_id};resting:{resting_order.order_id}",
                                order_id=resting_order.order_id,
                                symbol=resting_order.symbol,
                                side=resting_order.side,
                                price=price,
                                quantity=fill_qty,
                                remaining_quantity=resting_order.remaining_quantity,
                                timestamp=datetime.now(),
                                buyer_id=resting_order.client_id,
                                seller_id=incoming_order.client_id,
                                engine_destination_addr=incoming_order.engine_origin_addr,
                            ),
                        )
                    )

                    # Remove filled orders
                    if resting_order.remaining_quantity <= 0:
                        orders.remove(resting_order)
                        del active_orders[resting_order.order_id]
                    if incoming_order.remaining_quantity <= 0:
                        # orders.remove(incoming_order)
                        del active_orders[incoming_order.order_id]
                else:
                    orders.remove(resting_order)

        return {"incoming_fills": incoming_fills, "resting_fills": resting_fills}
