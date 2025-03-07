# main.py

from fastapi import FastAPI
from routers import motion_router

app = FastAPI(title="Multi-Camera WebSocket Streaming")

# Include the camera router
app.include_router(motion_router.router, prefix="/motion")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
