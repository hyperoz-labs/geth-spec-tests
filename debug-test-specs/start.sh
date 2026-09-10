#!/bin/bash
set -e

echo "=========================================="
echo "Geth Test Node - Complete Setup"
echo "=========================================="
echo ""
echo "This will:"
echo "  1. Initialize Geth with genesis.json"
echo "  2. Import blocks from blocks.bin (contains all transactions)"
echo "  3. Start Geth node with debug APIs"
echo ""

# Build and start all services
echo "Starting all services..."
docker compose up --build -d geth

echo ""
echo "Waiting for Geth node to be ready..."
sleep 5

# Wait for geth to be healthy
echo "Checking node health..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker compose ps geth | grep -q "healthy"; then
        echo "✓ Geth node is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "  Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "✗ Geth node failed to become healthy"
    echo "Check logs with: docker compose logs geth"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Your Geth node is running with:"
echo "  - Genesis block initialized"
echo "  - 35 blocks imported from blocks.bin (all transactions included)"
echo ""
echo "RPC endpoint: http://localhost:8545"
echo "WebSocket: ws://localhost:8546"
echo ""
echo "Useful commands:"
echo "  - View Geth logs: docker compose logs -f geth"
echo "  - Test debug RPC: ./test-debug-rpc.sh"
echo "  - Stop node: docker compose down"
echo "  - Restart fresh: docker compose down -v && ./start.sh"
echo ""
