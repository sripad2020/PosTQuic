from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

class BaseProtocolAdapter(ABC):
    def __init__(self, name: str, protocol_code: str):
        self.name = name
        self.protocol_code = protocol_code.upper()

    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate protocol-specific configuration dictionary."""
        pass

    @abstractmethod
    async def execute(
        self,
        config: Dict[str, Any],
        execution_mode: str,
        network_route: str,
        proxy_profile: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute request and return complete response object with metrics and packet trace."""
        pass

    def supports_proxy(self) -> bool:
        return True

    def supports_tls(self) -> bool:
        return True

    def supports_ipv6(self) -> bool:
        return True

    def supports_migration(self) -> bool:
        return False
