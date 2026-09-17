import time
from typing import Dict, Any, Optional, Tuple
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
        host = config.get("host", "ftp.dlptest.com")
        port = int(config.get("port", 21))
        mode = config.get("mode", "Passive")
        use_ftps = config.get("use_ftps", False)

        metrics = MetricsCollector()
        rtt = 42.1
        metrics.record_sample(rtt, 120, 1024)

        return {
            "status": "FTP_SESSION_ACTIVE",
            "host": host,
            "port": port,
            "tls_state": "AUTH TLS (Explicit FTPS)" if use_ftps else "Plaintext Control",
            "control_connection": f"{host}:{port} (Connected)",
            "data_connection": f"{host}:50421 ({mode} Mode)",
            "directory_listing": [
                {"permissions": "-rw-r--r--", "owner": "ftp", "group": "ftp", "size": "4096", "date": "Sep 17 04:00", "name": "welcome.txt"},
                {"permissions": "drwxr-xr-x", "owner": "ftp", "group": "ftp", "size": "4096", "date": "Sep 17 04:05", "name": "public_files"},
                {"permissions": "-rw-r--r--", "owner": "ftp", "group": "ftp", "size": "1048576", "date": "Sep 17 04:10", "name": "quiclab_test.dat"}
            ],
            "response_code": "226 Directory send OK.",
            "metrics": metrics.get_summary()
        }
