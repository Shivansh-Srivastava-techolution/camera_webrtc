import cv2
import asyncio
import base64
import logging
import time
from collections import deque
from starlette.websockets import WebSocket
from services.camera.utils import configure_camera

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
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.fps = fps
        self.cap = None
        self.frame_buffer = deque(maxlen=10)  # Increased buffer size to prevent frame drops

        self.init_camera()
        logging.info(f"Camera {source} initialized - {self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)} at {self.cap.get(cv2.CAP_PROP_FPS)} FPS")

    def init_camera(self):
        self.cap = cv2.VideoCapture(self.source)
        configure_camera(self.cap, self.frame_width, self.frame_height, self.fps)

    def log_fps_on_frame(self, frame, elapsed_time, fps, frame_count, start_time):
        frame_count += 1

        if elapsed_time >= 1.0:  # Every 1 second, calculate FPS
            fps = frame_count / elapsed_time
            logging.info(f"Server FPS: {fps:.2f}")  # Log FPS
            
            # Reset counters
            frame_count = 0
            start_time = time.perf_counter()  # More precise timing

        # Overlay FPS on the frame (optional)
        cv2.putText(frame, f"FPS: {fps:.2f}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 255, 0), 2, cv2.LINE_AA)

        return start_time, fps, frame_count, frame  # Return all updated values

    async def capture_frames(self):
        """ Continuously capture frames and store them in deque with FPS calculation """
        frame_count = 0
        start_time = time.perf_counter()
        fps = 0.0

        while self.cap.isOpened():
            capture_start = time.perf_counter()  # Measure time precisely
            
            ret, frame = await asyncio.to_thread(self.cap.read)
            
            if not ret:
                logging.warning(f"Frame capture failed for camera {self.source}.")
                break

            elapsed_time = time.perf_counter() - start_time

            # Update FPS and frame with overlay
            start_time, fps, frame_count, frame = self.log_fps_on_frame(frame, elapsed_time, fps, frame_count, start_time)

            # Store the frame in deque
            if len(self.frame_buffer) >= self.frame_buffer.maxlen:
                self.frame_buffer.popleft()  # Remove oldest frame to prevent frame drop
            self.frame_buffer.append(frame)

            # Adjust delay to maintain FPS
            capture_time = time.perf_counter() - capture_start
            delay = max(0, (1 / self.fps) - capture_time)  # Ensure frame rate is maintained
            await asyncio.sleep(delay)

    async def stream_frames(self, websocket: WebSocket):
        """ Fetch frames from deque and stream them over WebSocket """
        try:
            logging.info(f"Client connected: {websocket.client}")

            while True:
                if not self.frame_buffer:
                    logging.warning("Frame buffer empty, waiting for frames...")
                    await asyncio.sleep(0.01)  # Prevent high CPU usage
                    continue

                frame = self.frame_buffer.popleft()  # Fetch the oldest frame

                # Try sending frame over WebSocket
                try:
                    await self.send_frame(websocket, frame)
                except Exception as e:
                    logging.warning(f"WebSocket closed, stopping streaming: {e}")
                    break  # Stop streaming when WebSocket is closed

                await asyncio.sleep(1 / self.fps)  # Maintain FPS for streaming
                
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
            logging.info(f"Frame from Camera {self.source} sent. Raw Frame Size: {len(frame_bytes) // 1024} KB")

        except Exception as e:
            logging.warning(f"Error sending frame (WebSocket closed): {e}")
            raise  # Stop streaming if the WebSocket is closed
