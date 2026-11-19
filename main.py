import os
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.ws import ws_router
from app.db.database import init_db

app = FastAPI(
    title="QUICLAB — Multi-Protocol Network, QUIC & HTTP/3 Workbench",
    description="Production-grade Postman-like multi-protocol testing and experimentation platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register REST & WS routers
app.include_router(router)
app.include_router(ws_router)


@app.on_event("startup")
async def _init_app():
    """Initialise DB and silence harmless aioquic background-task noise.

    When a QUIC handshake cannot complete (UDP/443 blocked or QUIC-inspected),
    aioquic's internal transmit tasks surface a bare ConnectionError that
    asyncio reports as 'Future exception was never retrieved'. It is benign —
    the engine already reports the real failure reason to the caller — so we
    drop only that specific message and delegate everything else to default.
    """
    try:
        init_db()
    except Exception:
        pass

    loop = asyncio.get_event_loop()
    default_handler = loop.get_exception_handler()

    def _handler(lp, context):
        exc = context.get("exception")
        msg = context.get("message", "")
        if isinstance(exc, ConnectionError) and "never retrieved" in msg:
            return  # benign aioquic transmit noise
        if default_handler is not None:
            default_handler(lp, context)
        else:
            lp.default_exception_handler(context)

    loop.set_exception_handler(_handler)


# Mount Frontend static directories
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    css_dir = os.path.join(FRONTEND_DIR, "css")
    js_dir = os.path.join(FRONTEND_DIR, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")

@app.get("/", include_in_schema=False)
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "QUICLAB FastAPI Backend Running. Frontend index.html not found."}

@app.get("/landing", include_in_schema=False)
@app.get("/landing.html", include_in_schema=False)
async def serve_landing():
    landing_path = os.path.join(os.path.dirname(__file__), "landing.html")
    if os.path.exists(landing_path):
        return FileResponse(landing_path)
    return {"message": "Landing page landing.html not found."}


if __name__ == "__main__":
    init_db()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
