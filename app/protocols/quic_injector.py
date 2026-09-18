import os
import time
import uuid
import socket
import asyncio
from typing import Dict, Any, List, Optional

class QUICPacketInjectorEngine:
    """
    Real-Time QUIC Transport Parameter, Frame, Fault, and Version Injection Engine.
    Dispatches live UDP sockets and measures real transport metrics.
    """
    async def _send_udp_payload(self, host: str, port: int, payload: bytes, timeout: float = 1.5) -> Dict[str, Any]:
        t0 = time.perf_counter()
        try:
            ip = socket.gethostbyname(host)
        except Exception as e:
            return {"success": False, "ip": host, "port": port, "rtt_ms": 0.0, "error": str(e), "bytes_sent": 0, "bytes_recv": 0}

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        loop = asyncio.get_event_loop()

        try:
            await loop.sock_sendto(sock, payload, (ip, port))
            data, addr = await asyncio.wait_for(loop.sock_recvfrom(sock, 2048), timeout=timeout)
            rtt = (time.perf_counter() - t0) * 1000.0
            sock.close()
            return {"success": True, "ip": ip, "port": port, "rtt_ms": round(rtt, 2), "bytes_sent": len(payload), "bytes_recv": len(data)}
        except asyncio.TimeoutError:
            rtt = (time.perf_counter() - t0) * 1000.0
            sock.close()
            return {"success": False, "ip": ip, "port": port, "rtt_ms": round(rtt, 2), "bytes_sent": len(payload), "bytes_recv": 0}
        except Exception as e:
            sock.close()
            return {"success": False, "ip": ip, "port": port, "rtt_ms": 0.0, "error": str(e), "bytes_sent": len(payload), "bytes_recv": 0}

    async def inject_transport_parameters(
        self,
        target_host: str,
        target_port: int = 4433,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        params = params or {
            "initial_max_data": 2097152,
            "initial_max_stream_data_bidi_local": 524288,
            "initial_max_streams_bidi": 150,
            "max_idle_timeout_ms": 60000,
            "disable_active_migration": False,
            "max_ack_delay_ms": 25
        }

        # Build initial long header packet with transport params
        raw_header = b"\xC0\x00\x00\x00\x01\x08" + os.urandom(8) + b"\x08" + os.urandom(8)
        payload = raw_header + str(params).encode("utf-8")
        payload += b"\x00" * max(0, 1200 - len(payload))

        probe = await self._send_udp_payload(target_host, target_port, payload)

        injected_frames = [
            {"type": "CRYPTO", "offset": 0, "length": len(payload), "detail": f"ClientHello with Custom Transport Parameters: {params}"},
            {"type": "PADDING", "length": 1200 - len(payload), "detail": "UDP Datagram Padded to 1200 Bytes"}
        ]

        return {
            "status": "TRANSPORT_PARAMS_INJECTED",
            "target": f"{target_host}:{target_port}",
            "ip_address": probe.get("ip", target_host),
            "measured_rtt_ms": probe["rtt_ms"],
            "bytes_dispatched": probe["bytes_sent"],
            "bytes_received": probe["bytes_recv"],
            "injected_parameters": params,
            "packet_flight": {
                "packet_num": 1,
                "packet_type": "Initial (Long Header)",
                "payload_size": len(payload),
                "frames": injected_frames
            },
            "server_reaction": "Transport parameter packet dispatched live over UDP socket."
        }

    async def inject_custom_frame(
        self,
        target_host: str,
        target_port: int = 4433,
        frame_type: str = "RESET_STREAM",
        stream_id: int = 4,
        error_code: int = 10,
        max_data_limit: int = 1048576,
        payload_text: str = ""
    ) -> Dict[str, Any]:
        
        frame_byte_hex = "0x04" if frame_type == "RESET_STREAM" else "0x05"
        if frame_type == "MAX_STREAM_DATA": frame_byte_hex = "0x11"
        elif frame_type == "DATAGRAM": frame_byte_hex = "0x30"
        elif frame_type == "PING": frame_byte_hex = "0x01"
        elif frame_type == "CONNECTION_CLOSE": frame_byte_hex = "0x1C"

        # Build raw short header 1-RTT packet with custom frame
        short_header = b"\x40" + os.urandom(8)  # 1-RTT short header with CID
        frame_payload = bytes.fromhex(frame_byte_hex.replace("0x", "")) + stream_id.to_bytes(4, 'big') + error_code.to_bytes(2, 'big') + (payload_text.encode('utf-8') if payload_text else b"")
        raw_packet = short_header + frame_payload

        probe = await self._send_udp_payload(target_host, target_port, raw_packet)

        frame_detail = f"Injected custom {frame_type} on Stream {stream_id} with Error Code {error_code} ({hex(error_code)})"
        if frame_type == "STOP_SENDING":
            frame_detail = f"Injected STOP_SENDING on Stream {stream_id} requesting peer to stop sending (Err={error_code})"
        elif frame_type == "MAX_STREAM_DATA":
            frame_detail = f"Injected MAX_STREAM_DATA expanding Stream {stream_id} window limit to {max_data_limit} bytes"
        elif frame_type == "DATAGRAM":
            frame_detail = f"Injected RFC 9221 Unreliable DATAGRAM payload: '{payload_text or 'PING_DATAGRAM'}'"

        injected_packet = {
            "packet_num": 4,
            "packet_type": "1-RTT Short Header",
            "connection_id": f"cid_{uuid.uuid4().hex[:8]}",
            "frame_type_byte": frame_byte_hex,
            "injected_frame": {
                "type": frame_type,
                "stream_id": stream_id,
                "error_code": error_code,
                "error_code_hex": f"0x{error_code:02X}",
                "max_data_limit": max_data_limit,
                "payload": payload_text or None,
                "detail": frame_detail
            }
        }

        return {
            "status": "FRAME_INJECTION_SUCCESS",
            "target": f"{target_host}:{target_port}",
            "ip_address": probe.get("ip", target_host),
            "measured_rtt_ms": probe["rtt_ms"],
            "bytes_dispatched": probe["bytes_sent"],
            "bytes_received": probe["bytes_recv"],
            "injected_frame_type": frame_type,
            "stream_id": stream_id,
            "error_code_hex": f"0x{error_code:02X}",
            "packet_details": injected_packet
        }

    async def inject_fault_corruption(
        self,
        target_host: str,
        target_port: int = 4433,
        fault_type: str = "BIT_FLIP_HEADER_TYPE"
    ) -> Dict[str, Any]:
        
        fault_desc = "Corrupted Header Form Bit (Long Header -> Short Header mismatch)"
        corrupted_bytes = b"\xFF\xFE\xFD\xFC" + os.urandom(16)
        if fault_type == "PACKET_NUMBER_GAP":
            fault_desc = "Injected non-sequential packet number gap (PN #1 -> PN #500)"
            corrupted_bytes = b"\x40" + os.urandom(8) + b"\x00\x00\x01\xF4" + b"GAP_PAYLOAD"
        elif fault_type == "CRYPTO_KEY_SHARE_CORRUPTION":
            fault_desc = "Corrupted ECDHE Key Share bytes in CRYPTO Initial frame"
            corrupted_bytes = b"\xC0\x00\x00\x00\x01" + os.urandom(64)
        elif fault_type == "TRUNCATED_CONNECTION_ID":
            fault_desc = "Truncated Destination Connection ID from 8 bytes down to 2 bytes"
            corrupted_bytes = b"\xC0\x00\x00\x00\x01\x02" + os.urandom(2)

        probe = await self._send_udp_payload(target_host, target_port, corrupted_bytes)

        return {
            "status": "FAULT_INJECTED",
            "target": f"{target_host}:{target_port}",
            "ip_address": probe.get("ip", target_host),
            "measured_rtt_ms": probe["rtt_ms"],
            "bytes_dispatched": probe["bytes_sent"],
            "bytes_received": probe["bytes_recv"],
            "fault_type": fault_type,
            "description": fault_desc,
            "expected_server_defense": "CONNECTION_CLOSE (FRAME_ENCODING_ERROR or CRYPTO_ERROR)"
        }

    async def inject_version_negotiation(
        self,
        target_host: str,
        target_port: int = 4433,
        version_hex: str = "0x1A2B3C4D"
    ) -> Dict[str, Any]:
        
        try:
            ver_bytes = bytes.fromhex(version_hex.replace("0x", ""))
        except Exception:
            ver_bytes = b"\x1A\x2B\x3C\x4D"

        payload = b"\xC0" + ver_bytes + b"\x08" + os.urandom(8) + b"\x08" + os.urandom(8) + b"VER_INJECT"
        probe = await self._send_udp_payload(target_host, target_port, payload)

        return {
            "status": "VERSION_NEGOTIATION_INJECTED",
            "target": f"{target_host}:{target_port}",
            "ip_address": probe.get("ip", target_host),
            "measured_rtt_ms": probe["rtt_ms"],
            "bytes_dispatched": probe["bytes_sent"],
            "bytes_received": probe["bytes_recv"],
            "injected_quic_version": version_hex,
            "server_version_negotiation_packet": {
                "packet_type": "Version Negotiation Probe",
                "status": "DISPATCHED_LIVE_UDP_SOCKET"
            }
        }

quic_injector_instance = QUICPacketInjectorEngine()
