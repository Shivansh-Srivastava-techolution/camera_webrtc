import cv2
import asyncio
import base64
import logging
import time
from collections import deque
from starlette.websockets import WebSocket

# Configure logging to save logs to a file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("server_logs.log"),  # Save logs to file
        logging.StreamHandler()  # Print logs to console
    ]
)

CHUNK_SIZE = 1024 * 512  # 512 KB per chunk

class CameraService:
    def __init__(self, source, frame_width, frame_height, fps):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        self.avg_fps = deque(maxlen=fps * 2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        logging.info(f"Camera ID: {source},\n Resolution: {self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)},\n FPS set: {self.cap.get(cv2.CAP_PROP_FPS)}")
        self.fps = fps

    async def stream_frames(self, websocket: WebSocket):
        """ Stream frames in chunks over WebSocket """
        try:
            logging.info(f"Client connected: {websocket.client}")

            start_time = time.perf_counter()
            while self.cap.isOpened():
                
                ret, frame = self.cap.read()
                if not ret:
                    logging.warning(f"Frame capture failed, stopping stream for camera_id {self.source}.")
                    break

                end_time = time.perf_counter()

                fps = 1 // (end_time - start_time)
                self.avg_fps.append(fps)
                avg_fps = sum(self.avg_fps) // len(self.avg_fps) if self.avg_fps else 0
                
                cv2.putText(frame, f"Average FPS: {avg_fps}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                

                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                frame_b64 = base64.b64encode(frame_bytes).decode("utf-8")

                # Send in chunks
                for i in range(0, len(frame_b64), CHUNK_SIZE):
                    chunk = frame_b64[i:i+CHUNK_SIZE]
                    await websocket.send_text(chunk)

                start_time = end_time

                await websocket.send_text("END")  # Indicate end of frame

                elapsed_time = time.perf_counter() - start_time
                logging.info(f"Frame of camera {self.source} sent in {elapsed_time:.3f} seconds")

                await asyncio.sleep(1 / 30)  # Approx 30 FPS
        except Exception as e:
            logging.error(f"Error streaming frames: {e}")
        finally:
            self.cap.release()
            logging.info(f"Client disconnected: {websocket.client}")
