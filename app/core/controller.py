import uuid
import asyncio
from typing import Dict, Any, Optional

from app.core.routing import NetworkRouteEngine
from app.core.proxy import ProxyManager
from app.core.session import ProtocolSession, SessionState
from app.protocols.http1_2 import HTTP1And2Adapter
from app.protocols.http3 import HTTP3Adapter
from app.protocols.quic import QUICAdapter
from app.protocols.tcp import RawTCPAdapter
from app.protocols.udp import RawUDPAdapter
from app.protocols.websocket import WebSocketAdapter
from app.protocols.ftp import FTPAdapter
from app.protocols.ssh_sftp import SSHSFTPAdapter
from app.protocols.dns import DNSAdapter
from app.protocols.rtp import RTPAdapter, MoQAdapter, WebTransportAdapter
from app.protocols.openssl_diag import OpenSSLAdapter

class TestController:
    def __init__(self):
        self.adapters = {
            "HTTP/1.1": HTTP1And2Adapter(),
            "HTTP/2": HTTP1And2Adapter(),
            "HTTP/3": HTTP3Adapter(),
            "QUIC": QUICAdapter(),
            "RAW QUIC": QUICAdapter(),
            "RAW TCP": RawTCPAdapter(),
            "RAW UDP": RawUDPAdapter(),
            "WEBSOCKET": WebSocketAdapter(),
            "FTP": FTPAdapter(),
            "FTPS": FTPAdapter(),
            "SSH": SSHSFTPAdapter(),
            "SFTP": SSHSFTPAdapter(),
            "DNS": DNSAdapter(),
            "RTP": RTPAdapter(),
            "MOQ": MoQAdapter(),
            "WEBTRANSPORT": WebTransportAdapter(),
            "OPENSSL": OpenSSLAdapter()
        }

    def resolve_variables(self, text: str, env_vars: Dict[str, str]) -> str:
        """Resolves template variables e.g. {{base_url}}"""
        if not text or not isinstance(text, str):
            return text
        res = text
        for k, v in env_vars.items():
            res = res.replace(f"{{{{{k}}}}}", str(v))
        return res

    async def execute_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes request through complete pipeline:
        Request Validation -> Execution Mode -> Network Route -> Compatibility Check -> Protocol Adapter -> Target
        """
        protocol = payload.get("protocol", "HTTP/1.1").upper()
        execution_mode = payload.get("execution_mode", "Local")
        network_route = payload.get("network_route", "Existing Network")
        proxy_id = payload.get("proxy_profile_id", "direct-profile")
        config = payload.get("config", {})
        env_vars = payload.get("env_vars", {})

        # 1. Resolve template variables in config
        resolved_config = {}
        for k, v in config.items():
            if isinstance(v, str):
                resolved_config[k] = self.resolve_variables(v, env_vars)
            elif isinstance(v, dict):
                resolved_config[k] = {sub_k: self.resolve_variables(sub_v, env_vars) if isinstance(sub_v, str) else sub_v for sub_k, sub_v in v.items()}
            else:
                resolved_config[k] = v

        # 2. Resolve Effective Proxy Profile
        proxy_profile = NetworkRouteEngine.resolve_effective_proxy(request_proxy=proxy_id)

        # 3. Compatibility Engine Validation
        is_compatible, error_details = NetworkRouteEngine.validate_compatibility(
            protocol=protocol,
            execution_mode=execution_mode,
            network_route=network_route,
            proxy_profile=proxy_profile
        )

        target_str = resolved_config.get("url") or resolved_config.get("host") or resolved_config.get("domain") or "Target Endpoint"
        effective_route = NetworkRouteEngine.get_effective_route_summary(
            protocol=protocol,
            execution_mode=execution_mode,
            network_route=network_route,
            proxy_profile=proxy_profile,
            target_host=target_str
        )

        if not is_compatible:
            return {
                "success": False,
                "status": "PROXY INCOMPATIBLE",
                "effective_route": effective_route,
                "error": error_details
            }

        # 4. Get Protocol Adapter
        adapter = self.adapters.get(protocol)
        if not adapter:
            # Fallback to HTTP adapter if unmapped
            adapter = self.adapters["HTTP/1.1"]

        # Validate adapter config
        val_ok, val_err = adapter.validate_configuration(resolved_config)
        if not val_ok:
            return {
                "success": False,
                "status": "CONFIGURATION_ERROR",
                "effective_route": effective_route,
                "error": {"reason": val_err}
            }

        # 5. Initialize Session Lifecycle
        session = ProtocolSession(
            session_id=str(uuid.uuid4())[:8],
            protocol=protocol,
            target=target_str,
            execution_mode=execution_mode,
            network_route=network_route
        )

        session.transition_to(SessionState.CONNECTING, f"Connecting to {target_str}")
        session.transition_to(SessionState.CONNECTED, "Connection established")
        session.transition_to(SessionState.ACTIVE, f"Executing {protocol} payload transaction")

        # 6. Dispatch Execution
        try:
            res_data = await adapter.execute(
                config=resolved_config,
                execution_mode=execution_mode,
                network_route=network_route,
                proxy_profile=proxy_profile
            )

            session.transition_to(SessionState.CLOSING, "Transaction completed, gracefully closing session")
            session.transition_to(SessionState.CLOSED, "Session closed")

            return {
                "success": True,
                "status": "COMPLETED",
                "effective_route": effective_route,
                "session": session.to_dict(),
                "result": res_data
            }

        except Exception as e:
            session.transition_to(SessionState.FAILED, str(e))
            return {
                "success": False,
                "status": "EXECUTION_FAILED",
                "effective_route": effective_route,
                "session": session.to_dict(),
                "error": {"reason": str(e)}
            }

# Global Controller instance
controller_instance = TestController()
