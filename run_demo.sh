#!/bin/bash

echo "========================================="
echo "HVRT Demo Script"
echo "========================================="

echo ""
echo "Step 1: Starting services..."
echo "Please run these commands in separate terminals:"
echo ""
echo "  Terminal 1: python -m cta.main"
echo "  Terminal 2: python -m ec.main"
echo "  Terminal 3: python -m ag.main --port 8100"
echo "  Terminal 4: python -m ag.main --port 8200"
echo ""
read -p "Press Enter when all services are running..."

echo ""
echo "Step 2: Initializing system..."
python scripts/init_system.py

echo ""
echo "Step 3: Issuing device td001..."
python scripts/issue_device.py --device-id td001

echo ""
echo "Step 4: Initializing TD client..."
python -m td_client.main init --device-id td001

echo ""
echo "Step 5: Enrolling with AG1..."
python -m td_client.main enroll --device-id td001 --ag http://127.0.0.1:8100

echo ""
echo "Step 6: Accessing AG1..."
python -m td_client.main access --device-id td001 --ag http://127.0.0.1:8100

echo ""
echo "Step 7: Roaming to AG2..."
python -m td_client.main roam --device-id td001 --ag http://127.0.0.1:8200

echo ""
echo "========================================="
echo "Demo complete!"
echo "========================================="
