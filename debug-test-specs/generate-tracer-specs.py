#!/usr/bin/env python3
"""
Generic tracer spec generator for Geth debug tracers.
Supports tracers with and without config options.

For prestateTracer, automatically generates both diffMode variants:
- specs/prestate-tracer/diff-mode-false/
- specs/prestate-tracer/diff-mode-true/

For flatCallTracer, automatically generates default, convertParityErrors, and includePrecompiles variants:
- specs/flatcall-tracer/
- specs/flatcall-tracer/convert-parity-errors/
- specs/flatcall-tracer/include-precompiles/
Usage:
  python3 generate-tracer-specs.py [tracer-name]
  TRACER=flatTracer python3 generate-tracer-specs.py

Examples:
  python3 generate-tracer-specs.py 4byteTracer
  python3 generate-tracer-specs.py flatTracer
  TRACER=callTracer python3 generate-tracer-specs.py
  TRACER=prestateTracer python3 generate-tracer-specs.py
"""

import json
import os
import sys
import requests

# Configuration
RPC_URL = os.environ.get("RPC_URL", "http://localhost:8545")

# Get tracer name from command line argument or environment variable
TRACER = None
if len(sys.argv) > 1:
    TRACER = sys.argv[1]
else:
    TRACER = os.environ.get("TRACER")

if not TRACER:
    print("Error: No tracer specified!")
    print()
    print("Usage:")
    print("  python3 generate-tracer-specs.py [tracer-name]")
    print("  TRACER=flatTracer python3 generate-tracer-specs.py")
    print()
    print("Examples:")
    print("  python3 generate-tracer-specs.py 4byteTracer")
    print("  python3 generate-tracer-specs.py flatTracer")
    print("  python3 generate-tracer-specs.py callTracer")
    print("  python3 generate-tracer-specs.py prestateTracer")
    sys.exit(1)

# Normalize tracer name for directory (remove "Tracer" suffix if present, make lowercase)
tracer_dir_name = TRACER.replace("Tracer", "").lower() + "-tracer"

# Block definitions (block number and description)
BLOCKS = [
    ("0x0", "block-zero"),
    ("0x1", "empty"),
    ("0x2", "simple-transfer"),
    ("0x3", "self-destruct-contract"),
    ("0x4", "set-contract-storage"),
    ("0x5", "clear-storage"),
    ("0x6", "self-destruct-send-funds"),
    ("0x7", "increment-bytes"),
    ("0x8", "call-one-level-deep"),
    ("0x9", "call-multi-level-deep"),
    ("0xa", "callcode-one-level"),
    ("0xb", "delegate-call-one-level-deep"),
    ("0xc", "sequence-memory"),
    ("0xd", "MSTORE"),
    ("0xe", "increment-storage"),
    ("0xf", "logs"),
    ("0x10", "halts"),
    ("0x11", "push-swap"),
    ("0x12", "memory-read-revert"),
    ("0x13", "self-destruct"),
    ("0x14", "create-create2"),
    ("0x15", "set-and-clean-storage"),
    ("0x16", "set-and-clean-storage"),
    ("0x17", "static-call-one-level-deep"),
    ("0x18", "static-call-multiple-level-deeep"),
    ("0x19", "erc20-contract-transfer"),
    ("0x1a", "call-one-level-gas-refund"),
    ("0x1b", "self-destruct-send-self"),
    ("0x1c", "self-destruct-sender"),
    ("0x1d", "stack-underflow"),
    ("0x1e", "0g0v0_Istanbul"),
    ("0x1f", "precompile"),
    ("0x20", "contract-creation-fails-level-1"),
    ("0x21", "stack-underflow"),
    ("0x22", "failed-create-operations"),
    ("0x23", "create2-three-stack-items"),
    ("0x24", "extcode-and-balance-opcodes"),
    ("0x25", "eip7702-set-code-authorization"),
    ("0x26", "eip7702-call-delegated-eoa-directly"),
    ("0x27", "eip7702-call-delegated-eoa-via-proxy"),
    ("0x28", "deploy-log-contracts"),
    ("0x29", "logs-with-reverted-tx-and-frame"),
]

def rpc_call(method, params):
    """Make an RPC call to Geth"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1
    }
    response = requests.post(RPC_URL, json=payload)
    return response.json()

def generate_tx_spec(block_hex, tx_index, description, tracer_config, subdirectory):
    """Generate a debug_traceTransaction spec for the tx at tx_index of a block."""
    block = rpc_call("eth_getBlockByNumber", [block_hex, False])["result"]
    tx_hash = block["transactions"][tx_index]
    request = {
        "jsonrpc": "2.0",
        "method": "debug_traceTransaction",
        "params": [tx_hash, {"tracer": TRACER, "tracerConfig": tracer_config}],
        "id": 1
    }
    print(f"Querying tx {tx_hash} (block {block_hex} #{tx_index}, {description})...")
    response = rpc_call("debug_traceTransaction", request["params"])
    spec = {"request": request, "response": response, "statusCode": 200}
    index = int(block_hex, 16)
    filename = f"{index}-debug-{tracer_dir_name}-{block_hex}-{description}.json"
    filepath = os.path.join("specs", tracer_dir_name, subdirectory, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(spec, f, indent=2)
    print(f"  ✓ Created {os.path.join(subdirectory, filename)}")

def generate_spec(block_hex, description, index, tracer_config=None, subdirectory=None):
    """Generate a tracer spec file for a block

    Args:
        block_hex: Block number in hex format
        description: Block description
        index: Block index for filename
        tracer_config: Optional tracer configuration dict
        subdirectory: Optional subdirectory within tracer directory
    """

    # Build tracer params
    tracer_params = {"tracer": TRACER}
    if tracer_config:
        tracer_params["tracerConfig"] = tracer_config

    # Create request
    request = {
        "jsonrpc": "2.0",
        "method": "debug_traceBlockByNumber",
        "params": [
            block_hex,
            tracer_params
        ],
        "id": 1
    }

    # Query Geth
    config_label = f" (config: {tracer_config})" if tracer_config else ""
    print(f"Querying block {block_hex} ({description}){config_label}...")
    response = rpc_call("debug_traceBlockByNumber", [block_hex, tracer_params])

    # Build spec
    spec = {
        "request": request,
        "response": response,
        "statusCode": 200
    }

    # Generate filename and path
    filename = f"{index}-debug-{tracer_dir_name}-{block_hex}-{description}.json"
    if subdirectory:
        filepath = os.path.join("specs", tracer_dir_name, subdirectory, filename)
    else:
        filepath = os.path.join("specs", tracer_dir_name, filename)

    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Write file
    with open(filepath, 'w') as f:
        json.dump(spec, f, indent=2)

    relative_path = os.path.join(subdirectory, filename) if subdirectory else filename
    print(f"  ✓ Created {relative_path}")

    # Return result info for summary
    result = response.get("result", [])
    if isinstance(result, list):
        return len(result)
    return 0

def main():
    print("=" * 60)
    print(f"{TRACER} Spec Generator")
    print("=" * 60)
    print(f"Tracer: {TRACER}")

    # Check if this tracer needs special config handling
    needs_diff_mode = TRACER == "prestateTracer"
    needs_only_top_call = TRACER == "callTracer"
    needs_flat_variants = TRACER == "flatCallTracer"

    if needs_diff_mode:
        print(f"Output directories:")
        print(f"  - specs/{tracer_dir_name}/diff-mode-false/")
        print(f"  - specs/{tracer_dir_name}/diff-mode-true/")
        print(f"  - specs/{tracer_dir_name}/disable-code/")
        print(f"  - specs/{tracer_dir_name}/disable-storage/")
        print(f"  - specs/{tracer_dir_name}/include-empty/")
    elif needs_only_top_call:
        print(f"Output directories:")
        print(f"  - specs/{tracer_dir_name}/")
        print(f"  - specs/{tracer_dir_name}/only-top-call/")
    elif needs_flat_variants:
        print(f"Output directories:")
        print(f"  - specs/{tracer_dir_name}/")
        print(f"  - specs/{tracer_dir_name}/convert-parity-errors/")
        print(f"  - specs/{tracer_dir_name}/include-precompiles/")
    else:
        print(f"Output directory: specs/{tracer_dir_name}/")
    print()

    # Check if Geth is running
    try:
        response = rpc_call("eth_blockNumber", [])
        block_num = int(response.get("result", "0x0"), 16)
        print(f"✓ Connected to Geth node at {RPC_URL}")
        print(f"✓ Current block: {block_num}")
        print()
    except Exception as e:
        print(f"✗ Cannot connect to Geth node at {RPC_URL}")
        print(f"  Error: {e}")
        print(f"\nPlease start the node first:")
        print(f"  cd blockchain-generation && docker compose up -d geth")
        return 1

    # Generate specs for all blocks
    total_results = 0
    total_files = 0

    if needs_diff_mode:
        # Generate both diffMode variants for prestateTracer
        print("Generating diffMode: false specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(
                block_hex, description, index,
                tracer_config={"diffMode": False},
                subdirectory="diff-mode-false"
            )
            total_results += result_count
            total_files += 1

        print()
        print("Generating diffMode: true specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(
                block_hex, description, index,
                tracer_config={"diffMode": True},
                subdirectory="diff-mode-true"
            )
            total_results += result_count
            total_files += 1

        print()
        print("Generating disableCode: true specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(
                block_hex, description, index,
                tracer_config={"diffMode": False, "disableCode": True},
                subdirectory="disable-code"
            )
            total_results += result_count
            total_files += 1

        print()
        print("Generating disableStorage: true specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(
                block_hex, description, index,
                tracer_config={"diffMode": False, "disableStorage": True},
                subdirectory="disable-storage"
            )
            total_results += result_count
            total_files += 1

        print()
        print("Generating includeEmpty: true specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(
                block_hex, description, index,
                tracer_config={"diffMode": False, "includeEmpty": True},
                subdirectory="include-empty"
            )
            total_results += result_count
            total_files += 1
    elif needs_only_top_call:
        # Standard (onlyTopCall defaults to false) generation, plus an explicit
        # onlyTopCall: true variant so the nested-call-pruning behaviour has spec coverage.
        print("Generating default (onlyTopCall: false) specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(block_hex, description, index)
            total_results += result_count
            total_files += 1

        print()
        print("Generating onlyTopCall: true specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(
                block_hex, description, index,
                tracer_config={"onlyTopCall": True},
                subdirectory="only-top-call"
            )
            total_results += result_count
            total_files += 1

        # withLog: true variants (log index is block-wide, matching eth_getBlockReceipts logIndex),
        # with and without onlyTopCall, plus a debug_traceTransaction spec for a non-first tx.
        print()
        print("Generating withLog: true specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(
                block_hex, description, index,
                tracer_config={"withLog": True},
                subdirectory="with-log"
            )
            total_results += result_count
            total_files += 1

        print()
        print("Generating withLog: true, onlyTopCall: true specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(
                block_hex, description, index,
                tracer_config={"withLog": True, "onlyTopCall": True},
                subdirectory="with-log/only-top-call"
            )
            total_results += result_count
            total_files += 1

        print()
        print("Generating withLog: true debug_traceTransaction spec...")
        print("-" * 60)
        generate_tx_spec("0xf", 1, "logs-second-transaction", {"withLog": True}, "with-log")
        total_files += 1
        generate_tx_spec("0x29", 2, "logs-after-reverted-tx-third-transaction", {"withLog": True}, "with-log")
        total_files += 1
    elif needs_flat_variants:
        # Standard (convertParityErrors: false, includePrecompiles: false) generation,
        # plus convertParityErrors and includePrecompiles variants.
        print("Generating default (convertParityErrors: false, includePrecompiles: false) specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(block_hex, description, index)
            total_results += result_count
            total_files += 1

        print()
        print("Generating convertParityErrors: true specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(
                block_hex, description, index,
                tracer_config={"convertParityErrors": True},
                subdirectory="convert-parity-errors"
            )
            total_results += result_count
            total_files += 1

        print()
        print("Generating includePrecompiles: true specs...")
        print("-" * 60)
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(
                block_hex, description, index,
                tracer_config={"includePrecompiles": True},
                subdirectory="include-precompiles"
            )
            total_results += result_count
            total_files += 1
    else:
        # Standard generation without config
        for index, (block_hex, description) in enumerate(BLOCKS):
            result_count = generate_spec(block_hex, description, index)
            total_results += result_count
            total_files += 1

    print()
    print("=" * 60)
    print("✓ Generation Complete!")
    print("=" * 60)
    print()
    print(f"Tracer: {TRACER}")
    print(f"Generated: {total_files} spec files")
    print(f"Total results: {total_results}")
    print()
    if needs_diff_mode:
        print(f"Files created in:")
        print(f"  - specs/{tracer_dir_name}/diff-mode-false/")
        print(f"  - specs/{tracer_dir_name}/diff-mode-true/")
    elif needs_only_top_call:
        print(f"Files created in:")
        print(f"  - specs/{tracer_dir_name}/")
        print(f"  - specs/{tracer_dir_name}/only-top-call/")
    elif needs_flat_variants:
        print(f"Files created in:")
        print(f"  - specs/{tracer_dir_name}/")
        print(f"  - specs/{tracer_dir_name}/convert-parity-errors/")
        print(f"  - specs/{tracer_dir_name}/include-precompiles/")
    else:
        print(f"Files created in: specs/{tracer_dir_name}/")

    return 0


if __name__ == "__main__":
    exit(main())
