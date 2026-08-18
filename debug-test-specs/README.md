# Debug Test Specifications

This directory contains the original chain data, tracer specifications, and testing tools.

## Contents

- **../chain-data/** - Blockchain data (shared at top level)
  - `genesis.json` - Genesis configuration (Chain ID 1982)
  - `blocks.bin` - 33 pre-built blocks with transactions (original)
  - `blocks.json` - Transaction definitions (editable)

- **specs/** - Tracer specification files (JSON request/response pairs)
  - `call-tracer/` - 34 callTracer specs (hierarchical call traces), plus `call-tracer/only-top-call/` - 34 specs with `tracerConfig: {"onlyTopCall": true}` (nested `calls` pruned)
  - `flatcall-tracer/` - 34 flatCallTracer specs (flat call traces)
  - `prestate-tracer/` - 66 prestateTracer specs (diff-mode true/false)
  - `4byte-tracer/` - 34 4byteTracer specs

- **Docker files:**
  - `docker-compose.yml` - Test node (port 8545) and spec generator
  - `Dockerfile.spec-generator` - Spec generator image
  - `start.sh` - Start test node script

- **Scripts:**
  - `generate-tracer-specs.py` - Generic script to generate specs for any tracer
  - `generate-4byte-specs.py` - Legacy 4ByteTracer spec generator
  - `test-debug-rpc.sh` - Debug RPC test script

## Usage

### Start Test Node
```bash
./start.sh
```

This starts the Geth test node on port 8545 with debug APIs enabled.

### Test Debug RPC
```bash
./test-debug-rpc.sh
```

### Generate Tracer Specs

**Using Docker (recommended):**
```bash
# Make sure test node is running
./start.sh

# Generate flatCallTracer specs
TRACER=flatCallTracer docker compose up --build spec-generator

# Generate callTracer specs
TRACER=callTracer docker compose up --build spec-generator

# Generate prestateTracer specs
TRACER=prestateTracer docker compose up --build spec-generator

# Generate 4byteTracer specs (default)
docker compose up --build spec-generator
```

`TRACER=callTracer` generates both `specs/call-tracer/` (`onlyTopCall` defaults to false) and `specs/call-tracer/only-top-call/` (`tracerConfig: {"onlyTopCall": true}`), the same way `TRACER=prestateTracer` generates its `diff-mode-false/`/`diff-mode-true/` pair.

**Manual generation (without Docker):**
```bash
# Make sure Geth is running first
./start.sh

# Then generate specs in another terminal
python3 -m venv venv
source venv/bin/activate
pip install requests

# Generate flatCallTracer specs
export RPC_URL=http://localhost:8545
python3 generate-tracer-specs.py flatCallTracer

# Or using environment variable
TRACER=callTracer python3 generate-tracer-specs.py

deactivate
```

### Edit blockchain data
Edit `../chain-data/blocks.json` to modify transactions, then regenerate the blockchain using tools in `../blockchain-generation/`.

## Spec File Format

All specs follow this structure:
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

Tracers that accept configuration (e.g. callTracer's `onlyTopCall`, prestateTracer's `diffMode`) nest it under `tracerConfig` in the request params:
```json
{"tracer": "callTracer", "tracerConfig": {"onlyTopCall": true}}
```
