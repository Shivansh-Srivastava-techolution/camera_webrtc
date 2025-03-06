from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.motion.motion_service import MotionService
from services.motion.config import MOTION_CONFIG

router = APIRouter()

motion_services = {
    0: MotionService(source=MOTION_CONFIG['source'], 
                    frame_width=MOTION_CONFIG['frame_width'], 
                    frame_height=MOTION_CONFIG['frame_width'], 
                    fps=MOTION_CONFIG['fps']),
}

@router.websocket("/ws/motion/{cam_id}")
async def stream_motion_camera(websocket: WebSocket, cam_id: int):
    """ WebSocket endpoint for motion-based streaming """
    await websocket.accept()
    if cam_id not in motion_services:
        await websocket.send_text("Invalid camera ID")
        await websocket.close()
        return

    camera = motion_services[cam_id]
    
    try:
        await camera.stream_frames(websocket)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for Motion Camera {cam_id}")
