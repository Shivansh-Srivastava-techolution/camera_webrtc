import asyncio
import websockets
import cv2
import numpy as np
import base64
import logging

# Configure logging to save logs to a file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("client_logs.log"),  # Save logs to file
        logging.StreamHandler()  # Print logs to console
    ]
)

CAMERA_IDS = [0, 2, 4, 6]
WEBSOCKET_URLS = {cam_id: f"ws://localhost:8001/camera/ws/{cam_id}" for cam_id in CAMERA_IDS}

frame_buffers = {cam_id: "" for cam_id in CAMERA_IDS}

async def receive_stream(cam_id, url):
    """ Connects to WebSocket, receives frame chunks, and displays complete frames using OpenCV. """
    try:
        async with websockets.connect(url) as websocket:
            logging.info(f"Connected to WebSocket for Camera {cam_id}")

            while True:
                chunk = await websocket.recv()
                
                if chunk == "END":
                    frame_bytes = base64.b64decode(frame_buffers[cam_id])
                    frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
                    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

                    if frame is not None:
                        cv2.imshow(f"Camera {cam_id}", frame)

                        # Make the OpenCV window smaller without resizing the video
                        cv2.resizeWindow(f"Camera {cam_id}", 320, 240)

                    frame_buffers[cam_id] = ""  # Reset for next frame
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                else:
                    frame_buffers[cam_id] += chunk  # Append chunk to buffer

    except Exception as e:
        logging.error(f"Error receiving from Camera {cam_id}: {e}")
    finally:
        logging.info(f"Disconnected from Camera {cam_id}")

async def main():
    """ Runs multiple WebSocket clients in parallel to receive all camera streams. """
    tasks = [receive_stream(cam_id, url) for cam_id, url in WEBSOCKET_URLS.items()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
