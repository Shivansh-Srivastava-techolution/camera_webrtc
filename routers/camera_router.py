import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.camera.camera_service import CameraService
from core.config import CONFIG
from services.camera.config import CAMERA_CONFIGS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

router = APIRouter()


camera_id = CONFIG['camera_id']
# Initialize a new camera service dynamically for each request
camera = CameraService(
    source=CAMERA_CONFIGS[camera_id]["source"],
    frame_width=CAMERA_CONFIGS[camera_id]["frame_width"],
    frame_height=CAMERA_CONFIGS[camera_id]["frame_height"],
    fps=CAMERA_CONFIGS[camera_id]["fps"]
)

@router.websocket("/{cam_id}")
async def stream_camera(websocket: WebSocket, cam_id: str):
    """ WebSocket endpoint for real-time camera streaming """

    cam_id = int(cam_id)  # Convert cam_id from string to int
    await websocket.accept()
    client_ip = websocket.client.host if websocket.client else "Unknown"
    logging.info(f"WebSocket connection opened for Camera {cam_id} from {client_ip}")

    # Validate camera ID
    if cam_id != camera_id:
        logging.warning(f"Invalid camera ID requested: {cam_id}")
        await websocket.send_text("Invalid camera ID")
        await websocket.close()
        return

    try:
        # Start both capture_frames (producer) and stream_frames (consumer) concurrently
        capture_task = asyncio.create_task(camera.capture_frames())  # Produces frames
        stream_task = asyncio.create_task(camera.stream_frames(websocket))  # Consumes frames
        
        await asyncio.gather(capture_task, stream_task)  # Run both tasks together
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected for Camera {camera_id} from {client_ip}")
    finally:
        # Ensure camera resource is always released
        camera.cap.release()
        logging.info(f"Camera {camera_id} resource released")
