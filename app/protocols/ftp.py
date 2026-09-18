import time
import socket
import asyncio
from ftplib import FTP, FTP_TLS
from typing import Dict, Any, Optional, Tuple, List
from app.protocols.base import BaseProtocolAdapter
from app.core.metrics import MetricsCollector

class FTPAdapter(BaseProtocolAdapter):
    def __init__(self):
        super().__init__("FTP / FTPS Engine", "FTP")

    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not config.get("host"):
            return False, "FTP Server Host is required."
        return True, None

    async def execute(
        self,
        config: Dict[str, Any],
        execution_mode: str,
        network_route: str,
        proxy_profile: Optional[Any] = None
    ) -> Dict[str, Any]:
        host = config.get("host")
        if not host:
            return {"status": "FTP_CONNECTION_FAILED", "error": "Target host missing"}
            
        port = int(config.get("port", 21))
        mode = config.get("mode", "Passive")
        use_ftps = config.get("use_ftps", False)
        username = config.get("username", "anonymous")
        password = config.get("password", "anonymous@quiclab.io")

        metrics = MetricsCollector()
        t0 = time.perf_counter()

        def _run_ftp_session() -> Dict[str, Any]:
            if use_ftps:
                ftp = FTP_TLS()
            else:
                ftp = FTP()
            
            ftp.connect(host=host, port=port, timeout=5.0)
            if use_ftps:
                ftp.auth()
                ftp.prot_p()

            login_msg = ftp.login(user=username, passwd=password)
            ftp.set_pasv(mode.lower() == "passive")

            lines: List[str] = []
            ftp.retrlines('LIST', lines.append)
            welcome_msg = ftp.getwelcome()
            ftp.quit()

            # Parse directory listing lines into structured JSON
            parsed_dir = []
            for line in lines[:20]:  # Cap at top 20 items
                parts = line.split(maxsplit=8)
                if len(parts) >= 9:
                    parsed_dir.append({
                        "permissions": parts[0],
                        "owner": parts[2],
                        "group": parts[3],
                        "size": parts[4],
                        "date": f"{parts[5]} {parts[6]} {parts[7]}",
                        "name": parts[8]
                    })
                else:
                    parsed_dir.append({"raw": line})

            return {
                "welcome": welcome_msg,
                "login_response": login_msg,
                "lines": lines,
                "parsed_dir": parsed_dir
            }

        loop = asyncio.get_event_loop()
        try:
            res = await loop.run_in_executor(None, _run_ftp_session)
            rtt = (time.perf_counter() - t0) * 1000.0
            
            bytes_rx = sum(len(line) for line in res["lines"])
            metrics.record_sample(rtt, 120, max(bytes_rx, 256))

            return {
                "status": "FTP_SESSION_ACTIVE",
                "host": host,
                "port": port,
                "tls_state": "AUTH TLS (Explicit FTPS)" if use_ftps else "Plaintext Control",
                "control_connection": f"{host}:{port} (Connected)",
                "data_connection": f"{host}:{port} ({mode} Mode)",
                "welcome_banner": res["welcome"],
                "directory_listing": res["parsed_dir"] or [{"raw": line} for line in res["lines"][:15]],
                "total_items_found": len(res["lines"]),
                "rtt_ms": round(rtt, 2),
                "response_code": res["login_response"],
                "metrics": metrics.get_summary()
            }
        except Exception as e:
            # Fallback to direct TCP control socket banner check if FTP login or passive data port blocked
            t1 = time.perf_counter()
            try:
                conn = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: socket.create_connection((host, port), timeout=4.0)
                )
                banner = conn.recv(1024).decode("utf-8", errors="ignore")
                conn.close()
                rtt = (time.perf_counter() - t1) * 1000.0
                metrics.record_sample(rtt, 64, len(banner))
                return {
                    "status": "FTP_CONTROL_PORT_OPEN",
                    "host": host,
                    "port": port,
                    "tls_state": "AUTH TLS" if use_ftps else "Plaintext Control",
                    "welcome_banner": banner.strip(),
                    "rtt_ms": round(rtt, 2),
                    "note": f"Control port connected. FTP payload note: {str(e)}",
                    "metrics": metrics.get_summary()
                }
            except Exception as sock_e:
                rtt = (time.perf_counter() - t0) * 1000.0
                return {
                    "status": "FTP_CONNECTION_FAILED",
                    "host": host,
                    "port": port,
                    "error": f"FTP connection error: {str(e)}",
                    "rtt_ms": round(rtt, 2),
                    "metrics": metrics.get_summary()
                }

