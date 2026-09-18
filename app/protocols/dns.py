import time
import socket
import asyncio
import struct
from typing import Dict, Any, Optional, Tuple, List
from app.protocols.base import BaseProtocolAdapter
from app.core.metrics import MetricsCollector

class DNSAdapter(BaseProtocolAdapter):
    def __init__(self):
        super().__init__("DNS Resolver Engine", "DNS")

    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not config.get("domain"):
            return False, "Target Domain is required for DNS query."
        return True, None

    def _build_dns_query(self, domain: str, record_type: str = "A") -> Tuple[bytes, int]:
        """Encodes domain and record type into RFC 1035 wire-format DNS query packet."""
        tx_id = int(time.time() * 1000) & 0xFFFF
        flags = 0x0100  # Standard query with recursion desired
        qdcount = 1
        ancount = nscount = arcount = 0
        header = struct.pack(">HHHHHH", tx_id, flags, qdcount, ancount, nscount, arcount)

        qname = b""
        for part in domain.strip(".").split("."):
            encoded_part = part.encode("utf-8")
            qname += bytes([len(encoded_part)]) + encoded_part
        qname += b"\x00"

        type_map = {
            "A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "PTR": 12,
            "MX": 15, "TXT": 16, "AAAA": 28, "SRV": 33, "CAA": 257
        }
        qtype = type_map.get(record_type.upper(), 1)
        qclass = 1  # IN (Internet)

        question = qname + struct.pack(">HH", qtype, qclass)
        return header + question, tx_id

    def _parse_dns_response(self, data: bytes, domain: str, record_type: str) -> List[Dict[str, Any]]:
        """Parses raw DNS response datagram wire format (RFC 1035)."""
        answers = []
        if len(data) < 12:
            return answers

        tx_id, flags, qdcount, ancount, nscount, arcount = struct.unpack(">HHHHHH", data[:12])
        offset = 12

        # Skip Question section
        for _ in range(qdcount):
            while offset < len(data) and data[offset] != 0:
                if (data[offset] & 0xC0) == 0xC0:
                    offset += 2
                    break
                else:
                    offset += 1 + data[offset]
            else:
                offset += 1
            offset += 4  # qtype (2) + qclass (2)

        # Parse Answer section
        for _ in range(ancount):
            if offset >= len(data):
                break
            
            # Read name (handle compression pointers)
            if (data[offset] & 0xC0) == 0xC0:
                offset += 2
            else:
                while offset < len(data) and data[offset] != 0:
                    offset += 1 + data[offset]
                offset += 1

            if offset + 10 > len(data):
                break

            rtype, rclass, ttl, rdlength = struct.unpack(">HHIH", data[offset:offset+10])
            offset += 10
            rdata_bytes = data[offset:offset+rdlength]
            offset += rdlength

            # Decode Record Data
            parsed_val = ""
            if rtype == 1 and rdlength == 4:  # A Record
                parsed_val = socket.inet_ntoa(rdata_bytes)
            elif rtype == 28 and rdlength == 16:  # AAAA Record
                parsed_val = socket.inet_ntop(socket.AF_INET6, rdata_bytes)
            elif rtype in [2, 5, 12]:  # NS, CNAME, PTR
                parsed_val = rdata_bytes.decode("utf-8", errors="ignore")
            elif rtype == 15:  # MX
                pref = struct.unpack(">H", rdata_bytes[:2])[0]
                parsed_val = f"{pref} {rdata_bytes[2:].decode('utf-8', errors='ignore')}"
            elif rtype == 16:  # TXT
                parsed_val = rdata_bytes.decode("utf-8", errors="ignore")
            else:
                parsed_val = rdata_bytes.hex()

            type_name_map = {1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR", 15: "MX", 16: "TXT", 28: "AAAA"}
            answers.append({
                "name": domain,
                "type": type_name_map.get(rtype, str(rtype)),
                "ttl": ttl,
                "data": parsed_val or f"Raw ({rdlength} bytes)"
            })

        return answers

    async def execute(
        self,
        config: Dict[str, Any],
        execution_mode: str,
        network_route: str,
        proxy_profile: Optional[Any] = None
    ) -> Dict[str, Any]:
        domain = config.get("domain", "google.com")
        record_type = config.get("record_type", "A").upper()
        resolver_ip = config.get("resolver", "8.8.8.8")
        timeout = float(config.get("timeout", 3.0))

        metrics = MetricsCollector()
        t0 = time.perf_counter()

        # Try dnspython first if available for high-level resolution
        try:
            import dns.resolver
            my_resolver = dns.resolver.Resolver(configure=False)
            my_resolver.nameservers = [resolver_ip]
            my_resolver.timeout = timeout
            my_resolver.lifetime = timeout
            
            t1 = time.perf_counter()
            answers_objs = await asyncio.get_event_loop().run_in_executor(
                None, lambda: my_resolver.resolve(domain, record_type)
            )
            rtt = (time.perf_counter() - t1) * 1000.0

            answers = []
            for rdata in answers_objs:
                answers.append({
                    "name": domain,
                    "type": record_type,
                    "ttl": getattr(answers_objs, "ttl", 300),
                    "data": str(rdata)
                })

            metrics.record_sample(rtt, 32, len(str(answers)))

            return {
                "status": "NOERROR",
                "domain": domain,
                "record_type": record_type,
                "resolver": resolver_ip,
                "resolution_time_ms": round(rtt, 2),
                "answers": answers,
                "metrics": metrics.get_summary()
            }
        except Exception:
            pass

        # Fallback to direct native UDP socket DNS wire-format query (RFC 1035)
        try:
            query_bytes, tx_id = self._build_dns_query(domain, record_type)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            loop = asyncio.get_event_loop()

            t1 = time.perf_counter()
            await loop.sock_sendto(sock, query_bytes, (resolver_ip, 53))
            resp_data, _ = await asyncio.wait_for(loop.sock_recvfrom(sock, 4096), timeout=timeout)
            rtt = (time.perf_counter() - t1) * 1000.0
            sock.close()

            answers = self._parse_dns_response(resp_data, domain, record_type)
            metrics.record_sample(rtt, len(query_bytes), len(resp_data))

            return {
                "status": "NOERROR" if answers else "NXDOMAIN_OR_NO_ANSWER",
                "domain": domain,
                "record_type": record_type,
                "resolver": resolver_ip,
                "resolution_time_ms": round(rtt, 2),
                "answers": answers or [{"name": domain, "type": record_type, "ttl": 0, "data": "No record answer returned"}],
                "metrics": metrics.get_summary()
            }
        except Exception as e:
            # Fallback to native system getaddrinfo if DNS socket is blocked by local firewall
            t1 = time.perf_counter()
            try:
                addr_info = await asyncio.get_event_loop().getaddrinfo(domain, None)
                rtt = (time.perf_counter() - t1) * 1000.0
                unique_ips = list(set(item[4][0] for item in addr_info if item[4]))
                answers = [{"name": domain, "type": "A/AAAA", "ttl": 300, "data": ip} for ip in unique_ips]
                return {
                    "status": "NOERROR (SYSTEM_RESOLVER)",
                    "domain": domain,
                    "record_type": record_type,
                    "resolver": "System DNS",
                    "resolution_time_ms": round(rtt, 2),
                    "answers": answers,
                    "metrics": metrics.get_summary()
                }
            except Exception as sys_e:
                rtt = (time.perf_counter() - t1) * 1000.0
                return {
                    "status": "DNS_ERROR",
                    "domain": domain,
                    "record_type": record_type,
                    "resolver": resolver_ip,
                    "resolution_time_ms": round(rtt, 2),
                    "error": f"DNS resolution failed: {str(e)}",
                    "metrics": metrics.get_summary()
                }
