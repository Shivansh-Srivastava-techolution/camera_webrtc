#!/bin/bash

# Start FastAPI servers for each camera in separate processes
for cam_id in 0 2 4 6; do
    PORT=$((8001 + (cam_id / 2)))  # Assign ports dynamically
    echo "Starting camera server for cam_id=$cam_id on port=$PORT..."
    nohup uvicorn main:app --host 0.0.0.0 --port $PORT &
    sleep 2
done

echo "All camera servers started."
