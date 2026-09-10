# Geth Tracer Specification Tests

This project provides a complete test environment for generating and validating Ethereum tracer specifications. It runs a Geth node with a pre-built blockchain and generates tracer output specifications that can be used to validate alternative Ethereum client implementations (e.g., Besu).

## Overview

This repository contains **two independent projects**:

### 1. Tracer Specification Generator (`debug-test-specs/`)
Generates tracer specification files for validating Besu's tracer implementations against Geth.

**Purpose**: Create JSON request/response pairs for different tracers (callTracer, prestateTracer, 4byteTracer, etc.) that can be used as test fixtures in Besu's test suite.

**Components**:
- Pre-built Geth test node with 33 blocks covering various EVM scenarios
- Python scripts to query debug APIs and generate spec files
- 202 generated spec files ready for Besu integration (includes callTracer's `onlyTopCall: true` variant, generated the same way as prestateTracer's diffMode true/false variants)

**Technology**: Python 3.11+, Docker

### 2. Blockchain Generator (`blockchain-generation/`)
Generates custom blockchain data by replaying transactions from `blocks.json`.

**Purpose**: Create new blockchain test data when you need to add or modify test transactions. The generated blockchain can be exported and used by the spec generator above.

**Components**:
- Node.js + Web3.js transaction executor
- Synchronized block generation with 100% exact matching
- Handles reverting transactions (stack underflows, invalid opcodes)

**Technology**: Node.js 20+, Geth v1.14.12, Docker

---

**Typical workflow**:
1. Use `blockchain-generation/` if you need to add new test transactions
2. Use `debug-test-specs/` to generate tracer specs for Besu validation

## Prerequisites

**Required for both projects:**
- Docker
- Docker Compose

**Optional (for local development):**
- Python 3.11+ (for `debug-test-specs/` - tracer spec generation)
- Node.js 20+ (for `blockchain-generation/` - blockchain generation)

## Quick Start

### Project 1: Tracer Spec Generation (debug-test-specs/)

#### 1. Start Geth Node

Initialize and start the Geth test node:

```bash
cd debug-test-specs
chmod +x start.sh test-debug-rpc.sh
./start.sh
```

This will:
- Initialize Geth with the custom genesis configuration
- Import 33 pre-built test blocks
- Start Geth with debug APIs enabled
- Make RPC available at http://localhost:8545

#### 2. Verify Node is Running

```bash
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://localhost:8545
```

Expected: `{"jsonrpc":"2.0","id":1,"result":"0x21"}` (33 blocks)

#### 3. Test Debug APIs

```bash
cd debug-test-specs && ./test-debug-rpc.sh
```

### Project 2: Blockchain Generation (blockchain-generation/)

#### 1. Generate Blockchain

Generate blockchain from transactions defined in `blocks.json`:

```bash
cd blockchain-generation
docker compose -f docker-compose.generate-node.yml up
```

This will:
- Initialize Geth with `genesis.json` (Chain ID 1982)
- Execute all 53 transactions across 33 blocks
- Store result in `geth-data/` directory
- Stop automatically after completion (~3 minutes)

#### 2. Verify Generated Blockchain

```bash
cd blockchain-generation
docker compose -f docker-compose.query.yml up -d

curl -X POST http://localhost:8548 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

Expected: `{"jsonrpc":"2.0","id":1,"result":"0x21"}` (33 blocks)

#### 3. Cleanup

```bash
docker compose -f docker-compose.query.yml down
docker compose -f docker-compose.generate-node.yml down
rm -rf geth-data
```

## Project Structure

```
geth_spec_tests/
├── chain-data/                    # Shared blockchain data (top-level)
│   ├── genesis.json               # Genesis configuration (Chain ID 1982)
│   ├── blocks.json                # Transaction definitions (editable)
│   └── blocks.bin                 # Pre-built blocks (generated)
│
├── debug-test-specs/              # Test data and specifications
│   ├── specs/                     # Tracer specification files
│   │   ├── call-tracer/           # 34 callTracer specs
│   │   │   └── only-top-call/     # 34 callTracer specs with tracerConfig:{onlyTopCall:true}
│   │   ├── flatcall-tracer/       # 34 flatCallTracer specs
│   │   ├── prestate-tracer/       # 66 prestateTracer specs (diff-mode true/false)
│   │   ├── 4byte-tracer/          # 34 4byteTracer specs
│   │   └── README.md              # Specs documentation
│   ├── docker-compose.yml         # Test node and spec generator
│   ├── Dockerfile.spec-generator  # Spec generator image
│   ├── start.sh                   # Start test node script
│   ├── generate-tracer-specs.py   # Generic tracer spec generator
│   ├── generate-4byte-specs.py    # Legacy 4ByteTracer spec generator
│   ├── test-debug-rpc.sh          # Debug RPC test script
│   └── README.md                  # Documentation
│
├── blockchain-generation/         # Blockchain generation tools
│   ├── docker-compose.generate-node.yml # Generation node (port 8547)
│   ├── docker-compose.query.yml   # Query node for verification (port 8548)
│   ├── Dockerfile.combined-node   # Combined Geth + Node.js image
│   ├── generate-blocks.js         # Transaction executor (Node.js)
│   ├── package.json               # Node.js dependencies
│   ├── geth-data/                 # Generated blockchain database (bind mount)
│   └── README.md                  # Generation documentation
│
├── output/                        # Export output folder
│   └── .gitignore                 # Ignore *.bin files
│
└── README.md                      # This file
```

## Tracer Specifications

The `debug-test-specs/specs/` directory contains reference specifications for multiple tracers:

### callTracer (34 files, + 34 in `only-top-call/`)
Traces call execution including call types, addresses, gas usage, and data in a hierarchical structure.

**Example**: `specs/call-tracer/2-debug-call-tracer-0x2-simple-transfer.json`

`only-top-call/` mirrors every scenario with `tracerConfig: {"onlyTopCall": true}`, which asks the tracer to omit the nested `calls` array entirely (root call fields are unchanged).

**Example**: `specs/call-tracer/only-top-call/9-debug-call-tracer-0x9-call-multi-level-deep.json`

### flatCallTracer (34 files)
Provides a flat list of all calls (unlike the nested structure of callTracer), compatible with Parity/OpenEthereum trace format.

**Example**: `specs/flatcall-tracer/2-debug-flatcall-tracer-0x2-simple-transfer.json`

### prestateTracer (66 files)
Captures account state before and optionally after transaction execution.

**Modes**:
- `diff-mode-false/` (33 files) - Pre-state only
- `diff-mode-true/` (33 files) - Pre and post state

**Example**: `specs/prestate-tracer/diff-mode-true/block_0x2.json`

### 4byteTracer (34 files)
Detects function signatures (first 4 bytes) in transaction calldata.

**Example**: `specs/4byte-tracer/25-debug-4byte-tracer-0x19-erc20-contract-transfer.json`

### Spec File Format

All specs follow the same structure:

```json
{
  "request": {
    "jsonrpc": "2.0",
    "method": "debug_traceBlockByNumber",
    "params": ["0x2", {"tracer": "callTracer"}],
    "id": 1
  },
  "response": {
    "jsonrpc": "2.0",
    "id": 1,
    "result": [ /* tracer output */ ]
  },
  "statusCode": 200
}
```

## Generating New Blockchain Data

### Generate New Blockchain from blocks.json

To create a new blockchain with custom test cases:

```bash
# 1. Navigate to blockchain-generation directory
cd blockchain-generation

# 2. Edit transaction definitions (optional)
vim chain-data/blocks.json

# 3. Generate blockchain
docker compose -f docker-compose.generate-node.yml up
```

**What this does:**
- Initializes Geth with genesis.json (Chain ID 1982)
- Starts Geth with 5-second mining periods
- Executes all 53 transactions from `blocks.json` across 33 blocks
- Stops Geth automatically after completion (prevents extra empty blocks)
- Stores blockchain data in `geth-data/` folder (~360MB)
- Takes ~3 minutes to complete with 100% exact block matching

**Key Features:**
- ✅ Synchronized approach - waits for block N-1 before sending transactions for block N
- ✅ Parallel transaction sending per block (50-100ms total)
- ✅ Handles reverting transactions (stack underflows, invalid opcodes, reverts)
- ✅ Direct JSON-RPC to bypass Web3.js validation
- ✅ Auto-shutdown after completion

**Using the Generated Data:**

The generated blockchain is stored in the `blockchain-generation/geth-data/` folder (bind mount). You can:

1. **Use it directly for testing:**
   ```bash
   # Mount the folder in test containers
   docker run -v $(pwd)/blockchain-generation/geth-data:/root/.ethereum ethereum/client-go:latest ...
   ```

2. **Copy to another location:**
   ```bash
   cp -r blockchain-generation/geth-data/* /path/to/test/node/data/
   ```

3. **Query the generated blockchain:**
   ```bash
   # Start query node on port 8548
   cd blockchain-generation
   docker compose -f docker-compose.query.yml up -d

   # Test queries
   curl -X POST http://localhost:8548 -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
   ```

**Cleanup:**
```bash
# Stop and remove containers
docker compose -f docker-compose.generate-node.yml down

# Remove generated blockchain data
rm -rf geth-data
```

**Note:** Data is stored in a local directory (bind mount) rather than a Docker volume to avoid Docker Desktop disk space limitations.

### Add New Test Cases

To add new transactions to the blockchain:

1. **Edit chain-data/blocks.json:**
```json
{
  "blocks": [
    ...existing blocks...,
    {
      "number": 34,
      "comment": "Your new test case",
      "transactions": [
        {
          "comment": "Description",
          "secretKey": "0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3",
          "gasLimit": "0xFFFFF2",
          "gasPrice": "0xEF",
          "to": "0x...",
          "value": "0x01",
          "data": "0x..."
        }
      ]
    }
  ]
}
```

2. **Regenerate blockchain:**
```bash
cd blockchain-generation

# Clean previous data
docker compose -f docker-compose.generate-node.yml down
rm -rf geth-data

# Generate new blockchain
docker compose -f docker-compose.generate-node.yml up
```

### Check Block Generation Status

```bash
cd blockchain-generation

# View real-time logs
docker compose -f docker-compose.generate-node.yml logs -f

# View specific section
docker logs blockchain-generator 2>&1 | grep "Block [0-9]"

# Verify final state
docker logs blockchain-generator 2>&1 | grep -E "(Blockchain generation complete|Final block number)"
```

Expected output:
```
✓ Blockchain generation complete!
   Blocks generated: 32
   Transactions executed: 53
   Final block number: 33
```

## Generating Tracer Specs

### Generate Specs for Any Tracer

The project includes a generic spec generator that works with any Geth tracer.

**Generate specs using Docker:**

```bash
# Make sure Geth is running
cd debug-test-specs
./start.sh

# Generate flatCallTracer specs
TRACER=flatCallTracer docker compose up --build spec-generator

# Generate callTracer specs
TRACER=callTracer docker compose up --build spec-generator

# Generate prestateTracer specs
TRACER=prestateTracer docker compose up --build spec-generator

# Generate 4byteTracer specs (default if no TRACER specified)
docker compose up --build spec-generator
```

This queries every block listed by `generate-tracer-specs.py` and creates spec files in `debug-test-specs/specs/{tracer}-tracer/`.

`TRACER=callTracer` additionally generates a `debug-test-specs/specs/call-tracer/only-top-call/` variant with `tracerConfig: {"onlyTopCall": true}` for every block, the same way `TRACER=prestateTracer` generates both `diff-mode-false/` and `diff-mode-true/`.

### Manual Generation (without Docker)

```bash
cd debug-test-specs

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install requests

# Set RPC URL and generate specs
export RPC_URL=http://localhost:8545

# Pass tracer as argument
python3 generate-tracer-specs.py flatCallTracer

# Or use environment variable
TRACER=callTracer python3 generate-tracer-specs.py

deactivate
```

### Troubleshooting: Geth CLI flags changing under `latest`

Both `debug-test-specs/docker-compose.yml` (the test node) and Kurtosis-based external harnesses pin `ethereum/client-go:latest`, so a fresh pull can drop or rename flags between runs. If `./start.sh` fails to become healthy, check `docker compose logs geth` for `flag provided but not defined: ...` and remove/replace the offending flag in `docker-compose.yml`. `--allow-insecure-unlock` was one such flag removed by a recent Geth release; it was unnecessary here anyway since `--dev` mode auto-unlocks the dev account.

## Test Blockchain Coverage

The blocks through 0x23 cover:

- **Simple transfers** - ETH value transfers
- **Contract deployments** - CREATE and CREATE2
- **Contract calls** - CALL, CALLCODE, DELEGATECALL, STATICCALL
- **Storage operations** - SSTORE, SLOAD
- **Self-destructs** - SELFDESTRUCT with various scenarios
- **ERC20 operations** - Token contract deployment and transfers
- **Error cases** - Reverts, out-of-gas, invalid opcodes, stack underflows
- **Edge cases** - Empty blocks, precompiled contracts, gas refunds

## Docker Services

### geth-init
Initializes Geth data directory with genesis and imports blocks.bin. Runs once on first start.

### geth
Main Geth node with debug APIs enabled. Runs in dev mode for instant mining.

**Exposed Ports**:
- 8545 - HTTP RPC
- 8546 - WebSocket RPC

**Enabled APIs**: eth, net, web3, debug, personal, admin, miner, txpool

### spec-generator
Python service that queries the Geth node and generates tracer specification files.

## Managing the Geth Node

### Start Node
```bash
cd debug-test-specs
./start.sh
# or
docker compose up -d geth
```

### Stop Node
```bash
cd debug-test-specs
docker compose down
```

### View Logs
```bash
cd debug-test-specs
docker compose logs -f geth
docker compose logs geth-init
```

### Start Fresh (reset all data)
```bash
cd debug-test-specs
docker compose down -v
./start.sh
```

### Access Geth Console
```bash
cd debug-test-specs
docker compose exec geth geth attach http://localhost:8545
```

## Testing Tracers

### Test callTracer
```bash
curl -X POST -H "Content-Type: application/json" \
  --data '{
    "jsonrpc": "2.0",
    "method": "debug_traceBlockByNumber",
    "params": ["0x4", {"tracer": "callTracer"}],
    "id": 1
  }' \
  http://localhost:8545 | python3 -m json.tool
```

### Test prestateTracer
```bash
curl -X POST -H "Content-Type: application/json" \
  --data '{
    "jsonrpc": "2.0",
    "method": "debug_traceBlockByNumber",
    "params": ["0x2", {"tracer": "prestateTracer", "tracerConfig": {"diffMode": true}}],
    "id": 1
  }' \
  http://localhost:8545 | python3 -m json.tool
```

### Test 4byteTracer
```bash
curl -X POST -H "Content-Type: application/json" \
  --data '{
    "jsonrpc": "2.0",
    "method": "debug_traceBlockByNumber",
    "params": ["0x19", {"tracer": "4byteTracer"}],
    "id": 1
  }' \
  http://localhost:8545 | python3 -m json.tool
```

## Network Configuration

- **Chain ID**: 1982
- **Network ID**: 1982 (dev mode overrides this)
- **Consensus**: Proof-of-Authority (dev mode)
- **Block Time**: 0 seconds (instant mining with --dev.period 0)
- **Archive Mode**: Full state history retained
- **Peer Discovery**: Disabled (isolated node)

## Genesis Configuration

The genesis block includes:
- Pre-funded test accounts
- Pre-deployed test contracts (for storage operations, calls, etc.)
- EIP activations: All through Prague/Osaka
- Custom blob schedule configurations

See `chain-data/genesis.json` for full details.

## Use Cases

### 1. Validate Alternative Implementations
Use specs to verify that other Ethereum clients (e.g., Besu) produce identical tracer output to Geth.

### 2. Tracer Development
Reference implementations for developing new tracers or debugging existing ones.

### 3. Regression Testing
Ensure tracer output remains consistent across Geth versions.

### 4. Documentation
Provide concrete examples of tracer behavior for various transaction types.

## Troubleshooting

### Node won't start
```bash
docker compose logs geth-init
docker compose logs geth
```

Check for port conflicts (8545, 8546) or initialization errors.

### Spec generation fails
Ensure Geth is running and healthy:
```bash
docker compose ps
curl http://localhost:8545
```

### Old data causing issues
```bash
docker compose down -v
rm -rf geth-data
./start.sh
```

## Integration with Besu

The `debug-test-specs/specs/` directory can be copied into Besu's test suite to validate tracer implementations:

```java
@Test
void testCallTracer_Block0x4() {
  JsonNode spec = loadSpec("debug-test-specs/specs/call-tracer/4-debug-call-tracer-0x4-set-contract-storage.json");
  JsonNode actual = besu.debug_traceBlockByNumber("0x4", "callTracer");
  assertThat(actual).isEqualTo(spec.get("response").get("result"));
}
```

## Notes

- All blockchain data is stored in a Docker volume for persistence
- The `blocks.bin` file contains all transactions from `blocks.json` pre-executed
- Specs were generated from Geth v0.0.0-20251115140421 (custom build)
- Genesis block (0x0) cannot be traced (returns error)
- Block 0x1 is an empty block (no transactions)

### Technology Stack

**Blockchain Generation:**
- Geth v1.14.12 (Ethereum client)
- Node.js 20.x + Web3.js v4.15.0
- Docker + Docker Compose

**Synchronization Strategy:**
- Waits for block N-1 before submitting transactions for block N
- Sends all transactions for a block in parallel
- Verifies all transactions mined in correct block
- Uses direct HTTP JSON-RPC to bypass Web3.js validation
- Allows reverting transactions to be sent and mined on-chain

**Gas Price Handling:**
All transactions use their original `gasPrice` values from the source data, including 4 transactions with `gasPrice: "0x01"` (1 wei) in blocks 0x17, 0x1D, 0x1E, and 0x21. These low gas prices work correctly because the blockchain generation uses `--txpool.pricelimit 0` and `--txpool.pricebump 0` flags, which allow transactions with any gas price to be accepted and mined.

**Blockchain Export:**
After generation, the blockchain is automatically exported to `blocks.bin` (RLP-encoded format) which can be imported into any Geth instance using `geth import`. The export includes blocks 1-N (genesis block 0 is excluded as it's defined in `genesis.json`).

## Common Commands

### Test Node (Port 8545)
```bash
cd debug-test-specs

# Start test node
./start.sh

# Stop test node
docker compose down

# Reset and restart
docker compose down -v && ./start.sh

# View logs
docker compose logs -f geth

# Check block count
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://localhost:8545
```

### Block Generation (Port 8547)
```bash
cd blockchain-generation

# Generate blockchain
docker compose -f docker-compose.generate-node.yml up

# View logs
docker compose -f docker-compose.generate-node.yml logs -f

# Stop and clean up
docker compose -f docker-compose.generate-node.yml down
rm -rf geth-data

# Query generated blockchain (port 8548)
docker compose -f docker-compose.query.yml up -d
curl -X POST http://localhost:8548 -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
docker compose -f docker-compose.query.yml down
```

### Tracer Testing
```bash
# Test callTracer on block 4
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"debug_traceBlockByNumber","params":["0x4",{"tracer":"callTracer"}],"id":1}' \
  http://localhost:8545 | python3 -m json.tool

# Test prestateTracer with diff mode
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"debug_traceBlockByNumber","params":["0x2",{"tracer":"prestateTracer","tracerConfig":{"diffMode":true}}],"id":1}' \
  http://localhost:8545 | python3 -m json.tool

# Generate tracer specs
cd debug-test-specs
TRACER=flatCallTracer docker compose up --build spec-generator
```

## Contributing

To add new test cases:
1. Edit transaction definitions:
   ```bash
   vim chain-data/blocks.json
   ```

2. Regenerate blockchain:
   ```bash
   cd blockchain-generation
   docker compose -f docker-compose.generate-node.yml down
   rm -rf geth-data
   docker compose -f docker-compose.generate-node.yml up
   ```

3. Regenerate tracer specs (optional):
   ```bash
   cd debug-test-specs
   TRACER=flatCallTracer docker compose up --build spec-generator
   TRACER=callTracer docker compose up --build spec-generator
   ```

4. The chain-data is now shared at the top level - no copying needed!
   ```

## License

This is a test/reference project for Ethereum client development.
