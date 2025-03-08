# main.py

import sys
from core.config import CONFIG
from fastapi import FastAPI
from routers import camera_router

if len(sys.argv) > 1:
    camera_id = int(sys.argv[1])
    CONFIG['camera_id'] = camera_id
else:
    camera_id = 0

app = FastAPI(title="Multi-Camera WebSocket Streaming")

# Include the camera router
app.include_router(camera_router.router, prefix="/camera")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
