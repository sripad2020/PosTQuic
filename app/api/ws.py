import asyncio
import json
import random
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

ws_router = APIRouter()

@ws_router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            rtt = round(random.uniform(14.0, 26.0), 2)
            tp = round(random.uniform(45.0, 120.0), 1)
            packets = random.randint(100, 1500)
            streams = random.randint(1, 8)
            
            payload = {
                "timestamp": time.strftime("%H:%M:%S"),
                "rtt_ms": rtt,
                "throughput_mbps": tp,
                "packets_total": packets,
                "active_streams": streams,
                "status": "OPERATIONAL"
            }
            await websocket.send_json(payload)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass

@ws_router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    try:
        events = [
            "QUICLAB Test Controller Initialized",
            "Local Engine Ready",
            "Agent 127.0.0.1:9000 Handshake Verified",
            "Proxy Route Engine: Direct Active"
        ]
        for ev in events:
            await websocket.send_json({
                "timestamp": time.strftime("%H:%M:%S"),
                "level": "INFO",
                "message": ev
            })
            await asyncio.sleep(0.5)
        while True:
            await asyncio.sleep(10.0)
    except WebSocketDisconnect:
        pass
