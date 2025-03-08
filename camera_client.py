import asyncio
import websockets
import base64
import numpy as np
import cv2
import time

async def receive_motion_frames():
    uri = "ws://localhost:8001/camera/0"

    async with websockets.connect(uri) as websocket:
        frame_data = ""

        try:
            async for message in websocket:
                if message == "END":

                    # Decode and display the frame
                    frame_bytes = base64.b64decode(frame_data)
                    np_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                    if frame is not None:
                        cv2.imshow("Camera Stream", frame)
                        cv2.waitKey(1)  # Update display

                    frame_data = ""  # Reset for next frame

                else:
                    frame_data += message  # Append frame chunks

        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
        finally:
            cv2.destroyAllWindows()

asyncio.run(receive_motion_frames())