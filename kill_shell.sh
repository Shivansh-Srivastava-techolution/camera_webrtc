#!/bin/bash

for cam_id in 0 2 4 6; do
    PORT=$((8001 + (cam_id / 2)))  # Assign ports dynamically
    echo "Ending camera server for cam_id=$cam_id on port=$PORT..."
    kill -9 $(lsof -t -i:$PORT)
    sleep 1
done

echo "All camera servers stopped."
