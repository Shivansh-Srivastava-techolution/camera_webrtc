import cv2
import asyncio
import base64
import logging
import time
from starlette.websockets import WebSocket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("server_logs.log"),  # Save logs to file
        logging.StreamHandler()  # Print logs to console
    ]
)

CHUNK_SIZE = 1024 * 512  # 512 KB before Base64 encoding
BASE64_CHUNK_SIZE = (CHUNK_SIZE * 4) // 3  # Adjust for Base64 expansion

class CameraService:
    def __init__(self, source, frame_width, frame_height, fps):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        logging.info(f"Camera {source} - Resolution: {self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}, FPS: {self.cap.get(cv2.CAP_PROP_FPS)}")
        self.fps = fps

    async def stream_frames(self, websocket: WebSocket):
        """ Stream frames over WebSocket """
        try:
            logging.info(f"Client connected: {websocket.client}")

            start_time = time.perf_counter()
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    logging.warning(f"Frame capture failed, stopping stream for camera {self.source}.")
                    break

                # Calculate FPS
                end_time = time.perf_counter()
                fps = 1 / (end_time - start_time)
                start_time = end_time  # Reset FPS timer
                
                # Overlay FPS on the frame
                cv2.putText(frame, f"FPS: {fps:.2f}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

                # Send frame immediately (No buffer)
                await self.send_frame(websocket, frame)

                await asyncio.sleep(1 / self.fps)  # Approx 30 FPS
                
        except Exception as e:
            logging.error(f"Error streaming frames: {e}")
        finally:
            self.cap.release()
            logging.info(f"Client disconnected: {websocket.client}")

    async def send_frame(self, websocket: WebSocket, frame):
        """ Encodes and sends a frame over WebSocket with Fixed Chunk Size """
        try:
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            # Convert to Base64
            frame_b64 = base64.b64encode(frame_bytes).decode("utf-8")

            # Send in fixed-size chunks
            for i in range(0, len(frame_b64), BASE64_CHUNK_SIZE):
                chunk = frame_b64[i:i+BASE64_CHUNK_SIZE]
                await websocket.send_text(chunk)

            await websocket.send_text("END")  # Indicate end of frame

            logging.info(f"Frame from Camera {self.source} sent. Raw Frame Size: {len(frame_bytes) // 1024} KB, Base64 Chunk Size: {BASE64_CHUNK_SIZE // 1024} KB")
        except Exception as e:
            logging.error(f"Error encoding/sending frame: {e}")
