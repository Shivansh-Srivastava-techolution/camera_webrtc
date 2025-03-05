# main.py

from fastapi import FastAPI
from routers import camera_router

app = FastAPI(title="Multi-Camera WebSocket & HTTP Streaming")

# Include the camera router
app.include_router(camera_router.router, prefix="/camera")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
