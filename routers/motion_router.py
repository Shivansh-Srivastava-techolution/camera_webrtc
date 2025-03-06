from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.camera.camera_service import CameraService
from services.camera.config import CAMERA_CONFIGS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

router = APIRouter()

camera_services = {
    cam_id: CameraService(
        source=config["source"], 
        frame_width=config["frame_width"], 
        frame_height=config["frame_height"], 
        fps=config["fps"]
    ) for cam_id, config in CAMERA_CONFIGS.items()
}

@router.websocket("/ws/{cam_id}")
async def stream_camera(websocket: WebSocket, cam_id: int):
    """ WebSocket endpoint for real-time streaming """
    await websocket.accept()
    logging.info(f"WebSocket connection opened for Camera {cam_id}")

    if cam_id not in camera_services:
        logging.warning(f"Invalid camera ID requested: {cam_id}")
        await websocket.send_text("Invalid camera ID")
        await websocket.close()
        return

    camera = camera_services[cam_id]
    
    try:
        await camera.stream_frames(websocket)
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected for Camera {cam_id}")
