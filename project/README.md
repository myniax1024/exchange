# Distributed Order Matching Engine

A simple distributed order matching system that demonstrates how multiple matching engines can synchronize order books across different nodes. 


## Project Structure
```
├── client
│   ├── client.py
│   ├── custom_formatter.py
├── common
│   ├── orderbook.py
│   ├── order.py
├── engine
│   ├── cancel_fairy.py
│   ├── exchange.py
│   ├── match_engine.py
│   └── synchronizer.py
├── logs
│   ├── cancelfairy_logs
│   ├── client_logs
│   ├── engine_logs
│   ├── exchange_logs
│   ├── serve_logs
│   └── synchronizer_logs
├── network
│   ├── grpc_server.py
├── proto
│   ├── __init__.py
│   ├── matching_service_pb2_grpc.py
│   ├── matching_service_pb2.py
│   ├── matching_service_pb2.pyi
│   ├── matching_service.proto
├── README.md
├── requirements.txt
└── simulation
    ├── client_start.py
    ├── exchange_start.py
    ├── processes
    │   ├── start_exchange.py
    │   └── start_me.py
    ├── simulation.py
```

## Features
- Multiple matching engines forming a distributed exchange system
- Client API to allow custom trading logic
- Real-time order book synchronization
- Price-time priority matching
- Support for multiple trading pairs
- Support for limit orders and cancellations

## Assumptions
- Each matching machine has an orderbook and its own synchronizer to communicate with other engines
- Exchange service for matching engine discovery will be highly available


## Implementation Details
- A .proto file defines the structure of the messages and services that will be used for communication. It uses Google's language-agnostic data serialization format used with gRPC(protobuf). To generate gRPC code(you don't need to):
    ```bash
    python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/matching_service.proto
    ```
- python gRPC package is outdated, make sure you install the latest version of **grpcio**, dependencies in `requirements.txt`

## Testing

- From the top level directory, navigate to `simulation`. From here, you can edit the files `process/start_exchange.py` and `process/start_me.py` to modify the ip addresses at which the exchange and the matching engines will be located (by default these are on local host). Run the exchange script to create an exchange, and run the `start_me` script (multiple times if desired) to form an exchange with matching engines.

- From the top level directory, run `simulation/client_start.py` to run several predefined clients at the matching engines. Make sure to edit this file to reflect any changes to the exchange ip address if you changed it earlier. 

- If you want to implement your own bot, take a look at `client/automated_trader_template` and `simulation/client_examples/random_client.py`. All you need to implement is the logic for generating orders and the logic for handling fill information
