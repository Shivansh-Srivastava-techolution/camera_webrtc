import cv2
import asyncio
import base64
import logging
import time
from starlette.websockets import WebSocket
from services.motion.motion_detection import MotionDetection

logging.basicConfig(level=logging.INFO)

CHUNK_SIZE = 1024 * 512  # 512 KB before Base64 encoding
BASE64_CHUNK_SIZE = (CHUNK_SIZE * 4) // 3  # Adjust for Base64 expansion

class MotionService:
    def __init__(self, source, frame_width, frame_height, fps):
        self.source = source
        self.cap = cv2.VideoCapture(source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        logging.info(f"Camera {source} - Resolution: {self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}, FPS: {self.cap.get(cv2.CAP_PROP_FPS)}")
        self.fps = fps
        self.resolution = (f"{self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
        self.motion_detection = MotionDetection(fps)

    async def stream_frames(self, websocket: WebSocket):
        """ Stream frames only when motion is detected """
        try:
            logging.info(f"Client connected for motion-based streaming: {websocket.client}")

            start_time = time.perf_counter()
            while self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    logging.warning(f"Frame capture failed for camera {self.source}. Stopping stream.")
                    break

                # Detect motion
                self.motion_detection.update_motion_status(frame)

                if self.motion_detection.motion_detected:
                    # Calculate FPS
                    end_time = time.perf_counter()
                    fps = 1 / (end_time - start_time)
                    start_time = end_time  # Reset FPS timer
                    
                    # Overlay FPS
                    cv2.putText(frame, f"FPS: {fps:.2f} || Resolution: {self.resolution}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

                    # Send frame when motion is detected
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
            frame_b64 = base64.b64encode(frame_bytes).decode("utf-8")

            # Send in fixed-size chunks
            for i in range(0, len(frame_b64), BASE64_CHUNK_SIZE):
                chunk = frame_b64[i:i+BASE64_CHUNK_SIZE]
                await websocket.send_text(chunk)

            await websocket.send_text("END")  # Indicate end of frame
            logging.info(f"Motion detected! Frame from Camera {self.source} sent.")
        except Exception as e:
            logging.error(f"Error encoding/sending frame: {e}")
