from typing import Dict, Any, Optional, Tuple
from app.core.proxy import ProxyManager, ProxyProfile

class NetworkRouteEngine:
    """
    Network Route Engine & Scope Hierarchy Resolver.
    Effective configuration precedence:
    Request -> Session -> Collection -> Environment -> Global -> Default
    """
    
    @staticmethod
    def resolve_effective_proxy(
        request_proxy: Optional[str] = None,
        session_proxy: Optional[str] = None,
        collection_proxy: Optional[str] = None,
        env_proxy: Optional[str] = None,
        global_proxy: Optional[str] = None
    ) -> ProxyProfile:
        # Precedence resolution
        selected_id = (
            request_proxy or
            session_proxy or
            collection_proxy or
            env_proxy or
            global_proxy or
            "direct-profile"
        )
        profile = ProxyManager.get_profile_by_id(selected_id)
        if not profile:
            # Fallback to direct profile
            profile = ProxyProfile("direct-profile", "Direct (No Proxy)", "Direct", "localhost", 0)
        return profile

    @staticmethod
    def validate_compatibility(
        protocol: str,
        execution_mode: str,       # "Local" or "QUICLAB Agent"
        network_route: str,        # "Existing Network" or "Configured Proxy"
        proxy_profile: Optional[ProxyProfile] = None
    ) -> Tuple[bool, Optional[Dict[str, str]]]:
        """
        Validates whether the requested protocol can execute via the chosen network route.
        DO NOT automatically fall back from an incompatible proxy to direct networking.
        """
        if network_route == "Existing Network" or execution_mode == "QUICLAB Agent":
            # Direct or Agent proxying is natively supported
            return True, None

        if not proxy_profile or proxy_profile.proxy_type == "Direct":
            return True, None

        proxy_type = proxy_profile.proxy_type
        proto = protocol.upper()

        # Check unsupported protocol / proxy combinations
        incompatible_reasons = []

        if proto in ["QUIC", "RAW QUIC", "HTTP/3"]:
            if proxy_type == "HTTP Proxy":
                incompatible_reasons.append("Standard HTTP Proxy cannot transport raw UDP/QUIC frames or QUIC connection handshakes.")
            elif proxy_type == "HTTPS / CONNECT Proxy":
                incompatible_reasons.append("HTTP CONNECT tunnels TCP streams only and does not establish UDP association for QUIC/HTTP3.")

        elif proto in ["UDP", "RAW UDP", "RTP"]:
            if proxy_type in ["HTTP Proxy", "HTTPS / CONNECT Proxy"]:
                incompatible_reasons.append("HTTP and CONNECT proxies only support stream-based TCP transport and cannot handle UDP datagrams.")

        elif proto in ["TCP", "RAW TCP"]:
            if proxy_type == "HTTP Proxy":
                incompatible_reasons.append("HTTP Proxy requires HTTP protocol structure and does not support raw TCP socket streaming.")

        if incompatible_reasons:
            error_details = {
                "status": "PROXY INCOMPATIBLE",
                "protocol": protocol,
                "proxy_name": proxy_profile.name,
                "proxy_type": proxy_type,
                "reason": " ".join(incompatible_reasons),
                "action": "Configure a UDP-capable proxy (e.g., SOCKS5 with UDP Associate or QUICLAB Agent Proxy) or select Existing Network."
            }
            return False, error_details

        return True, None

    @staticmethod
    def get_effective_route_summary(
        protocol: str,
        execution_mode: str,
        network_route: str,
        proxy_profile: ProxyProfile,
        target_host: str
    ) -> Dict[str, Any]:
        route_nodes = ["UI", f"Execution ({execution_mode})"]
        
        if network_route == "Configured Proxy" and proxy_profile.proxy_type != "Direct":
            route_nodes.append(f"Proxy ({proxy_profile.name} - {proxy_profile.proxy_type})")
            
        route_nodes.append(f"Transport ({protocol})")
        route_nodes.append(f"Target ({target_host})")

        return {
            "execution": execution_mode,
            "network": network_route,
            "proxy": proxy_profile.name if network_route == "Configured Proxy" else "None (Direct)",
            "protocol": protocol,
            "route_diagram": " ↓ ".join(route_nodes),
            "nodes": route_nodes
        }
