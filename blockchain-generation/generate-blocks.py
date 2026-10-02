#!/usr/bin/env python3
"""
Generate blockchain from ../chain-data/blocks.json transaction definitions.

Replays each block's transactions against a running Geth node in --dev mode
(period 0, so a block is mined as soon as a transaction lands in the pool),
one block at a time, verifying each transaction is mined into the expected
block number before moving on to the next block.

Supports legacy transactions (secretKey/gasLimit/gasPrice/to/value/data) and
EIP-7702 SetCodeTransactions (type: 4, maxFeePerGas/maxPriorityFeePerGas,
authorizationList). Each authorizationList entry additionally carries
"authoritySecretKey" so the authorization signature is fully reproducible
from blocks.json alone, matching the declarative style of every other field.

Usage:
  python3 generate-blocks.py [--from-block N]
  RPC_URL=http://localhost:8545 python3 generate-blocks.py
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from eth_account import Account
from eth_utils import to_checksum_address

RPC_URL = os.environ.get("RPC_URL", "http://localhost:8545")
BLOCKS_JSON = os.environ.get(
    "BLOCKS_JSON", str(Path(__file__).resolve().parent.parent / "chain-data" / "blocks.json")
)


def rpc(method, params):
    response = requests.post(
        RPC_URL, json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1}, timeout=10
    )
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(f"{method} failed: {payload['error']}")
    return payload["result"]


def wait_for_geth(max_retries=30):
    for attempt in range(max_retries):
        try:
            block_num = int(rpc("eth_blockNumber", []), 16)
            print(f"Connected to Geth at {RPC_URL}, current block {block_num}")
            return block_num
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"Could not connect to Geth at {RPC_URL} after {max_retries}s")


def sign_transaction(tx_def, nonce_tracker, chain_id):
    sender = Account.from_key(tx_def["secretKey"])
    address = sender.address
    if address not in nonce_tracker:
        nonce_tracker[address] = int(rpc("eth_getTransactionCount", [address, "pending"]), 16)
    nonce = nonce_tracker[address]

    tx = {
        "nonce": nonce,
        "gas": int(tx_def["gasLimit"], 16),
        "value": int(tx_def.get("value", "0x0"), 16),
        "chainId": chain_id,
        "data": tx_def.get("data", "0x"),
    }
    if tx_def.get("to"):
        tx["to"] = to_checksum_address(tx_def["to"])

    if tx_def.get("type") == 4:
        tx["type"] = 4
        tx["maxFeePerGas"] = int(tx_def["maxFeePerGas"], 16)
        tx["maxPriorityFeePerGas"] = int(tx_def["maxPriorityFeePerGas"], 16)
        tx["accessList"] = []
        authorizations = []
        for auth_def in tx_def["authorizationList"]:
            auth = {
                "chainId": auth_def["chainId"],
                "address": to_checksum_address(auth_def["address"]),
                "nonce": auth_def["nonce"],
            }
            authorizations.append(
                Account.sign_authorization(auth, auth_def["authoritySecretKey"])
            )
        tx["authorizationList"] = authorizations
    else:
        tx["gasPrice"] = int(tx_def["gasPrice"], 16)

    signed = Account.sign_transaction(tx, tx_def["secretKey"])
    nonce_tracker[address] += 1
    return signed.raw_transaction, signed.hash.hex()


def wait_for_receipt(tx_hash, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        receipt = rpc("eth_getTransactionReceipt", [tx_hash])
        if receipt:
            return receipt
        time.sleep(0.25)
    raise RuntimeError(f"Transaction {tx_hash} not mined within {timeout}s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-block", type=lambda s: int(s, 0), default=None)
    args = parser.parse_args()

    blocks_data = json.loads(Path(BLOCKS_JSON).read_text())
    start_block = wait_for_geth()
    chain_id = int(rpc("eth_chainId", []), 16)
    print(f"Chain ID {chain_id}, starting from block {start_block}\n")

    expected_block = args.from_block if args.from_block is not None else start_block + 1
    block_count = 0
    tx_count = 0

    for block_def in blocks_data["blocks"]:
        raw_number = block_def["number"]
        block_num = raw_number if isinstance(raw_number, int) else int(raw_number, 16)
        if block_num < expected_block:
            continue

        transactions = block_def.get("transactions", [])
        print(f"Block {block_num}: {len(transactions)} transaction(s)")

        nonce_tracker = {}
        # Sign everything first, then submit in reverse nonce order: higher-nonce txs sit in the
        # pool as non-executable (gapped) until the lowest nonce arrives, which promotes them all
        # at once so --dev (period 0) seals them together in a single block.
        signed_txs = [sign_transaction(tx_def, nonce_tracker, chain_id) for tx_def in transactions]
        for raw, tx_hash in reversed(signed_txs):
            sent_hash = rpc("eth_sendRawTransaction", ["0x" + raw.hex()])
            assert sent_hash.lower() == ("0x" + tx_hash).lower(), (
                f"hash mismatch: sent {sent_hash} signed {tx_hash}"
            )
        for i, (tx_def, (_, tx_hash)) in enumerate(zip(transactions, signed_txs)):
            sent_hash = "0x" + tx_hash
            receipt = wait_for_receipt(sent_hash)
            mined_block = int(receipt["blockNumber"], 16)
            status = receipt["status"]
            comment = tx_def.get("comment", "")
            print(f"  tx{i}: {sent_hash} mined in block {mined_block} status={status} - {comment}")
            if mined_block != block_num:
                print(
                    f"  WARNING: expected block {block_num}, tx landed in {mined_block}"
                )
            tx_count += 1

        expected_block = block_num + 1
        block_count += 1

    final_block = int(rpc("eth_blockNumber", []), 16)
    print(f"\nDone. Blocks generated: {block_count}, transactions: {tx_count}")
    print(f"Final block number: {final_block}")


if __name__ == "__main__":
    main()
