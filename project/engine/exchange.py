import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import random
from typing import Dict

from client.custom_formatter import LogFactory


class Exchange:
    """Class that initializes matching engines, synchronizers, and bootstraps
    client connections to matching engines.
    """

    def __init__(self, me_data: Dict[str, Dict[str, str]], authentication_key: str):
        """
        me_data looks like {me_name: {location_x : <float>, location_y: <float>, address: <string>}}
        """
        self.name = "Exchange"
        self.me_data = me_data
        self.authentication_key = authentication_key

        # logging
        self.log_directory = os.getcwd() + "/logs/exchange_logs/"
        self.logger = LogFactory(self.name, self.log_directory).get_logger()

    def assign_client(self, client_x: float, client_y: float):
        """Assigns clients to matching engines.

        Returns a matching engine address drawn from self.me_data,
        based on distance
        """

        #        min_dist = (1 << 30)
        #        for name, data in self.me_data:
        #            current_distance = distance((client_x, client_y), (data["location_x"], data["location_y"]))
        #            if  current_distance < min_dist:
        #                min_dist = current_distance

        # TODO: Make this base on distance instead of random

        if len(list(self.me_data.keys())) == 0:
            self.logger.critical("no matching engines registered")

        matched_me_name = random.choice(list(self.me_data.keys()))
        self.logger.info(f"assigned client to {matched_me_name}")
        return self.me_data[matched_me_name]["address"]

    def authenticate(self, client_id: str, client_authentication: str):
        # TODO: Actually check password
        self.logger.info(f"authenticated client {client_id}")

        return True

    def authenticate_me(self, authentication_request):
        self.logger.info(f"authenticated me {authentication_request.engine_id}")
        # TODO: Actually check password
        return True

    async def register_me(self, registration_request):
        self.me_data.update(
            {
                registration_request.engine_id: {
                    "location_x": 0,
                    "location_y": 0,
                    "address": registration_request.engine_addr,
                }
            }
        )

    async def get_matching_engine_addresses(self):
        engine_addresses = []
        for engine_id in self.me_data.keys():
            engine_addresses.append(self.me_data[engine_id]["address"])

        return engine_addresses
