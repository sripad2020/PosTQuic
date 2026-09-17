from typing import Dict, Any, Optional, Tuple, List
from app.db.database import get_db

class ProxyProfile:
    def __init__(self, id: str, name: str, proxy_type: str, host: str, port: int, auth_type: str = "None",
                 username: Optional[str] = None, password: Optional[str] = None,
                 tls_config: Optional[Dict[str, Any]] = None, bypass_rules: Optional[List[str]] = None):
        self.id = id
        self.name = name
        self.proxy_type = proxy_type  # Direct, HTTP Proxy, HTTPS / CONNECT Proxy, SOCKS5, QUICLAB Agent Proxy
        self.host = host
        self.port = port
        self.auth_type = auth_type
        self.username = username
        self.password = password
        self.tls_config = tls_config or {}
        self.bypass_rules = bypass_rules or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "proxy_type": self.proxy_type,
            "host": self.host,
            "port": self.port,
            "auth_type": self.auth_type,
            "username": self.username,
            "tls_config": self.tls_config,
            "bypass_rules": self.bypass_rules
        }

class ProxyManager:
    @staticmethod
    def get_all_profiles() -> List[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM proxy_profiles")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    @staticmethod
    def get_profile_by_id(profile_id: str) -> Optional[ProxyProfile]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM proxy_profiles WHERE id = ?", (profile_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return ProxyProfile(
            id=row["id"],
            name=row["name"],
            proxy_type=row["proxy_type"],
            host=row["host"],
            port=row["port"],
            auth_type=row["auth_type"],
            username=row["username"],
            password=row["password_encrypted"],
            bypass_rules=json_parse(row["bypass_rules"])
        )

def json_parse(val: Any) -> Any:
    if isinstance(val, str):
        try:
            import json
            return json.loads(val)
        except Exception:
            return []
    return val or []
