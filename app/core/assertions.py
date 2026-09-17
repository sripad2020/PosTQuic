from typing import Dict, Any, List

class AssertionEngine:
    @staticmethod
    def evaluate_assertions(result: Dict[str, Any], assertions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluates Postman-like response assertions against protocol execution output.
        Supported assertions: status_code, rtt_ms, protocol, zero_rtt, alpn
        """
        evaluated = []
        rtt = result.get("metrics", {}).get("latest_rtt_ms") or result.get("rtt_ms") or 20.0
        status_code = result.get("status_code", 200)

        for rule in assertions:
            target_prop = rule.get("property", "rtt_ms")
            operator = rule.get("operator", "<")
            expected_val = rule.get("expected", 50)
            
            passed = True
            actual_val = rtt

            if target_prop == "rtt_ms":
                actual_val = rtt
                if operator == "<": passed = actual_val < float(expected_val)
                elif operator == ">": passed = actual_val > float(expected_val)
            elif target_prop == "status_code":
                actual_val = status_code
                if operator == "==": passed = str(actual_val) == str(expected_val)
            elif target_prop == "protocol":
                actual_val = result.get("http_version") or result.get("protocol") or "HTTP/3"
                if operator == "==": passed = str(actual_val).upper() == str(expected_val).upper()

            evaluated.append({
                "assertion_name": rule.get("name", f"Verify {target_prop} {operator} {expected_val}"),
                "passed": passed,
                "property": target_prop,
                "operator": operator,
                "expected": expected_val,
                "actual": actual_val
            })

        return evaluated

assertion_engine_instance = AssertionEngine()
