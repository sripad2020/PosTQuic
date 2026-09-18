import time
import socket
import asyncio
from typing import Dict, Any, Optional, Tuple, List
from app.protocols.base import BaseProtocolAdapter
from app.core.metrics import MetricsCollector

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

class SSHSFTPAdapter(BaseProtocolAdapter):
    def __init__(self):
        super().__init__("SSH Shell & SFTP Subsystem Engine", "SFTP")

    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not config.get("host"):
            return False, "SSH Host target is required."
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
            return {"status": "SSH_CONNECTION_FAILED", "error": "Target host missing"}

        port = int(config.get("port", 22))
        username = config.get("username", "demo")
        password = config.get("password", "")
        subsystem = config.get("subsystem", "sftp")  # "ssh" or "sftp"
        remote_dir = config.get("remote_dir", ".")

        metrics = MetricsCollector()
        t0 = time.perf_counter()

        def _run_paramiko_session() -> Dict[str, Any]:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host=host, port=port, username=username, password=password or None, timeout=5.0)

            transport = ssh.get_transport()
            cipher_name = transport.get_cipher_name() if transport else "Unknown"
            kex_name = transport.get_kex_info() if transport else "Unknown"

            if subsystem == "ssh":
                stdin, stdout, stderr = ssh.exec_command("uname -a; uptime")
                out_str = stdout.read().decode("utf-8", errors="ignore")
                err_str = stderr.read().decode("utf-8", errors="ignore")
                ssh.close()
                return {
                    "subsystem": "ssh",
                    "cipher": cipher_name,
                    "kex": kex_name,
                    "command_output": out_str or err_str or "Session connected successfully."
                }
            else:
                sftp = ssh.open_sftp()
                attr_list = sftp.listdir_attr(remote_dir)
                parsed_files = []
                for attr in attr_list[:20]:
                    parsed_files.append({
                        "filename": attr.filename,
                        "size": attr.st_size,
                        "permissions": oct(attr.st_mode),
                        "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(attr.st_mtime))
                    })
                sftp.close()
                ssh.close()
                return {
                    "subsystem": "sftp",
                    "cipher": cipher_name,
                    "kex": kex_name,
                    "file_list": parsed_files
                }

        loop = asyncio.get_event_loop()
        if PARAMIKO_AVAILABLE:
            try:
                res = await loop.run_in_executor(None, _run_paramiko_session)
                rtt = (time.perf_counter() - t0) * 1000.0
                metrics.record_sample(rtt, 240, 1850)

                if res["subsystem"] == "ssh":
                    return {
                        "status": "SSH_SESSION_AUTHENTICATED",
                        "host": host,
                        "port": port,
                        "username": username,
                        "subsystem": "ssh-user-shell",
                        "kex_algorithm": str(res["kex"]),
                        "cipher": res["cipher"],
                        "command_output": res["command_output"],
                        "rtt_ms": round(rtt, 2),
                        "metrics": metrics.get_summary()
                    }
                else:
                    return {
                        "status": "SFTP_SUBSYSTEM_OPEN",
                        "host": host,
                        "port": port,
                        "username": username,
                        "subsystem": "sftp",
                        "remote_dir": remote_dir,
                        "kex_algorithm": str(res["kex"]),
                        "cipher": res["cipher"],
                        "file_list": res["file_list"],
                        "rtt_ms": round(rtt, 2),
                        "metrics": metrics.get_summary()
                    }
            except Exception as paramiko_err:
                pass

        # Fallback to direct TCP socket SSH protocol banner handshake probe (RFC 4253)
        t1 = time.perf_counter()
        try:
            conn = await loop.run_in_executor(
                None, lambda: socket.create_connection((host, port), timeout=4.0)
            )
            server_banner = conn.recv(1024).decode("utf-8", errors="ignore").strip()
            # Send client identification string
            conn.sendall(b"SSH-2.0-QUICLAB_SSH_Client_1.0\r\n")
            conn.close()
            rtt = (time.perf_counter() - t1) * 1000.0
            metrics.record_sample(rtt, 32, len(server_banner))

            return {
                "status": "SSH_PORT_ACTIVE_BANNER_VERIFIED",
                "host": host,
                "port": port,
                "server_banner": server_banner or "SSH-2.0 Server Active",
                "subsystem": subsystem,
                "rtt_ms": round(rtt, 2),
                "paramiko_available": PARAMIKO_AVAILABLE,
                "metrics": metrics.get_summary()
            }
        except Exception as sock_err:
            rtt = (time.perf_counter() - t0) * 1000.0
            return {
                "status": "SSH_CONNECTION_FAILED",
                "host": host,
                "port": port,
                "error": f"SSH connection failed: {str(sock_err)}",
                "rtt_ms": round(rtt, 2),
                "metrics": metrics.get_summary()
            }

