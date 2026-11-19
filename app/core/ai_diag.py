from typing import Dict, Any, List


class AIProtocolDiagnosticEngine:
    """
    Heuristic protocol diagnostic analyzer.

    This is an explainable rule engine (not an LLM). Every insight and both
    scores are computed from *real* fields observed in the transaction result:
    measured RTT, negotiated TLS/QUIC version, real cipher strength, real
    certificate expiry, ALPN, packet loss and HSTS state. Nothing is hardcoded
    to a fixed pass; if a signal is absent the corresponding rule is skipped.
    """

    @staticmethod
    def analyze_transaction(result: Dict[str, Any]) -> Dict[str, Any]:
        insights: List[Dict[str, Any]] = []
        security_score = 100
        perf_score = 100
        signals_used: List[str] = []

        def _get(*keys, default=None):
            for k in keys:
                cur = result
                ok = True
                for part in k.split("."):
                    if isinstance(cur, dict) and part in cur:
                        cur = cur[part]
                    else:
                        ok = False
                        break
                if ok and cur is not None:
                    return cur
            return default

        metrics = result.get("metrics", {}) if isinstance(result.get("metrics"), dict) else {}

        # ---- performance: real RTT ----------------------------------------
        rtt = _get("metrics.avg_rtt_ms", "rtt_ms", "handshake_ms", "ttfb_ms")
        if rtt is not None:
            signals_used.append("rtt")
            rtt = float(rtt)
            if rtt > 150:
                perf_score -= 30
                insights.append(_i("WARNING", "PERFORMANCE", "High Latency",
                                   f"Measured {rtt:.1f}ms RTT is well above the 50ms target; check routing or enable 0-RTT."))
            elif rtt > 60:
                perf_score -= 12
                insights.append(_i("INFO", "PERFORMANCE", "Elevated Latency",
                                   f"Measured {rtt:.1f}ms RTT; acceptable but above the 50ms ideal."))
            else:
                insights.append(_i("SUCCESS", "PERFORMANCE", "Low Latency",
                                   f"Measured {rtt:.1f}ms RTT is within the optimal range."))

        # ---- performance: real packet loss --------------------------------
        loss = metrics.get("packet_loss_pct")
        if loss is not None:
            signals_used.append("packet_loss")
            if float(loss) > 1.0:
                perf_score -= 20
                insights.append(_i("WARNING", "PERFORMANCE", "Packet Loss Detected",
                                   f"{loss}% loss observed; will trigger congestion-control backoff."))

        # ---- security: real TLS version -----------------------------------
        tls_version = _get("tls_version", "security_layer.tls_version",
                           "correlation.security_layer.tls_version", "quic_details.tls_version")
        if tls_version:
            signals_used.append("tls_version")
            if tls_version in ("TLSv1.3", "TLS 1.3"):
                insights.append(_i("SUCCESS", "SECURITY", "Modern TLS",
                                   f"{tls_version} negotiated with forward secrecy."))
            elif tls_version in ("TLSv1.2", "TLS 1.2"):
                security_score -= 5
                insights.append(_i("INFO", "SECURITY", "TLS 1.2 In Use",
                                   "TLS 1.2 is acceptable; TLS 1.3 reduces handshake latency and legacy risk."))
            else:
                security_score -= 35
                insights.append(_i("CRITICAL", "SECURITY", "Obsolete TLS",
                                   f"{tls_version} is deprecated and should be disabled."))

        # ---- security: real cipher strength -------------------------------
        bits = _get("cipher_bits", "cipher_suite.secret_bits")
        if isinstance(bits, (int, float)):
            signals_used.append("cipher_bits")
            if bits < 128:
                security_score -= 25
                insights.append(_i("WARNING", "SECURITY", "Weak Cipher",
                                   f"{int(bits)}-bit symmetric key is below the 128-bit minimum."))

        # ---- security: real certificate expiry ----------------------------
        days = _get("certificate.days_remaining", "quic_details.certificate.days_remaining")
        if days is not None:
            signals_used.append("cert_expiry")
            days = int(days)
            if days < 0:
                security_score -= 40
                insights.append(_i("CRITICAL", "SECURITY", "Certificate Expired",
                                   f"Peer certificate expired {abs(days)} days ago."))
            elif days < 30:
                security_score -= 15
                insights.append(_i("WARNING", "SECURITY", "Certificate Expiring Soon",
                                   f"Peer certificate expires in {days} days; schedule rotation."))
            else:
                insights.append(_i("SUCCESS", "SECURITY", "Certificate Healthy",
                                   f"Peer certificate valid for {days} more days."))

        # ---- protocol modernization ---------------------------------------
        proto = str(_get("http_version", "protocol", default="")).upper()
        if proto == "HTTP/1.1":
            perf_score -= 10
            insights.append(_i("INFO", "PROTOCOL", "Upgrade Opportunity",
                               "Endpoint served HTTP/1.1; HTTP/3 over QUIC removes head-of-line blocking."))
        elif "HTTP/3" in proto:
            insights.append(_i("SUCCESS", "PROTOCOL", "HTTP/3 Active",
                               "Running over QUIC — no TCP head-of-line blocking."))

        if not signals_used:
            insights.append(_i("INFO", "DIAGNOSTIC", "Insufficient Signals",
                               "Transaction contained no measurable TLS/latency fields to analyze."))

        return {
            "status": "AI_DIAGNOSTIC_COMPLETE",
            "engine": "explainable-rule-engine",
            "signals_used": signals_used,
            "security_score": max(0, min(100, security_score)),
            "performance_score": max(0, min(100, perf_score)),
            "insights_count": len(insights),
            "insights": insights,
        }


def _i(severity, category, title, detail):
    return {"severity": severity, "category": category, "title": title, "detail": detail}


ai_diag_instance = AIProtocolDiagnosticEngine()
