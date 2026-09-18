from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.core.controller import controller_instance
from app.core.routing import NetworkRouteEngine
from app.core.proxy import ProxyManager
from app.agent.capability import AgentCapabilityManager
from app.lab.network_lab import lab_instance
from app.db.database import get_db

router = APIRouter(prefix="/api/v1")

class ExecuteRequestModel(BaseModel):
    protocol: str
    execution_mode: str = "Local"
    network_route: str = "Existing Network"
    proxy_profile_id: Optional[str] = "direct-profile"
    config: Dict[str, Any] = {}
    env_vars: Dict[str, Any] = {}

class ProxyValidateModel(BaseModel):
    protocol: str
    execution_mode: str
    network_route: str
    proxy_profile_id: str

@router.post("/execute")
async def execute_protocol_test(payload: ExecuteRequestModel):
    res = await controller_instance.execute_request(payload.model_dump())
    return res

@router.post("/compatibility/validate")
async def validate_compatibility(payload: ProxyValidateModel):
    proxy_profile = ProxyManager.get_profile_by_id(payload.proxy_profile_id)
    is_ok, err_details = NetworkRouteEngine.validate_compatibility(
        protocol=payload.protocol,
        execution_mode=payload.execution_mode,
        network_route=payload.network_route,
        proxy_profile=proxy_profile
    )
    return {
        "compatible": is_ok,
        "error_details": err_details
    }

@router.get("/proxies")
async def list_proxies():
    return ProxyManager.get_all_profiles()

@router.post("/proxies")
async def create_proxy(profile: Dict[str, Any]):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO proxy_profiles (id, name, proxy_type, host, port, auth_type, username, password_encrypted)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        profile.get("id", f"proxy_{profile.get('name', 'custom').lower().replace(' ', '_')}"),
        profile.get("name"),
        profile.get("proxy_type"),
        profile.get("host"),
        int(profile.get("port", 8080)),
        profile.get("auth_type", "None"),
        profile.get("username"),
        profile.get("password")
    ))
    conn.commit()
    conn.close()
    return {"status": "created"}

@router.get("/collections")
async def list_collections():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM collections")
    cols = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return cols

@router.post("/collections")
async def create_collection(payload: Dict[str, Any]):
    import os
    conn = get_db()
    cursor = conn.cursor()
    col_id = payload.get("id", f"col_{os.urandom(3).hex()}")
    cursor.execute("""
    INSERT INTO collections (id, name, description, variables)
    VALUES (?, ?, ?, ?)
    """, (col_id, payload.get("name", "New Collection"), payload.get("description", ""), str(payload.get("variables", "{}"))))
    conn.commit()
    conn.close()
    return {"status": "created", "id": col_id}

@router.delete("/collections/{col_id}")
async def delete_collection(col_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM collections WHERE id = ?", (col_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@router.get("/environments")
async def list_environments():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM environments")
    envs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return envs

@router.post("/environments")
async def create_environment(payload: Dict[str, Any]):
    conn = get_db()
    cursor = conn.cursor()
    env_id = payload.get("id", f"env_{payload.get('name', 'custom').lower().replace(' ', '_')}")
    cursor.execute("""
    INSERT INTO environments (id, name, variables, is_active)
    VALUES (?, ?, ?, ?)
    """, (env_id, payload.get("name"), payload.get("variables", "{}"), payload.get("is_active", 0)))
    conn.commit()
    conn.close()
    return {"status": "created", "id": env_id}

@router.post("/environments/{env_id}/activate")
async def activate_environment(env_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE environments SET is_active = 0")
    cursor.execute("UPDATE environments SET is_active = 1 WHERE id = ?", (env_id,))
    conn.commit()
    conn.close()
    return {"status": "activated", "id": env_id}

@router.delete("/environments/{env_id}")
async def delete_environment(env_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM environments WHERE id = ?", (env_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

@router.get("/sessions")
async def list_sessions():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY id DESC")
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sessions

@router.delete("/sessions")
async def clear_sessions():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()
    return {"status": "cleared"}


from app.fuzzing.fuzzer import fuzzer_instance
from app.stress.stress_runner import stress_runner_instance

@router.post("/fuzz/run")
async def run_fuzz_campaign(payload: Dict[str, Any]):
    host = payload.get("host", "quic.tech")
    port = int(payload.get("port", 4433))
    protocol = payload.get("protocol", "QUIC")
    iterations = int(payload.get("iterations", 10))
    return await fuzzer_instance.execute_fuzz_campaign(host, port, protocol, iterations)

@router.post("/stress/run")
async def run_stress_test(payload: Dict[str, Any]):
    url = payload.get("url", "https://cloudflare-quic.com/")
    concurrency = int(payload.get("concurrency", 50))
    total_requests = int(payload.get("total_requests", 200))
    return await stress_runner_instance.run_stress_test(url, concurrency, total_requests)

@router.get("/agent/capabilities")
async def get_agent_capabilities():
    return AgentCapabilityManager.discover_capabilities()

@router.get("/lab/config")
async def get_lab_config():
    return lab_instance.config

@router.post("/lab/config")
async def update_lab_config(config: Dict[str, Any]):
    return lab_instance.update_config(config)

from app.protocols.quic_advanced import adv_quic_engine_instance

def _extract_target(payload: Dict[str, Any]) -> tuple[str, int]:
    host = payload.get("host") or payload.get("target_host") or payload.get("target")
    if not host and payload.get("url"):
        raw_url = payload.get("url", "")
        host = raw_url.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    if not host:
        host = "127.0.0.1"
    port = int(payload.get("port", 4433))
    return host, port

@router.post("/quic/zerortt-test")
async def run_zerortt_test(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_zerortt_replay_test(host, port)

@router.post("/quic/qpack-analysis")
async def run_qpack_analysis(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_qpack_analysis(host, port)

@router.post("/quic/congestion-benchmark")
async def run_congestion_benchmark(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    algo = payload.get("algorithm", "BBR")
    return await adv_quic_engine_instance.run_congestion_benchmark(host, port, algo)

@router.post("/quic/pmtud-ecn-probe")
async def run_pmtud_ecn_probe(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_pmtud_ecn_probe(host, port)

@router.post("/quic/spinbit-privacy-audit")
async def run_spinbit_privacy_audit(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_spinbit_cid_privacy_audit(host, port)

@router.post("/quic/connection-migration-test")
async def run_connection_migration_test(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_connection_migration_test(host, port)

@router.post("/quic/datagram-extension-test")
async def run_datagram_extension_test(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_datagram_extension_test(host, port)

@router.post("/quic/ech-privacy-test")
async def run_ech_privacy_test(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_ech_sni_privacy_test(host, port)

@router.post("/quic/flow-control-test")
async def run_flow_control_test(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_flow_control_autotune_test(host, port)

@router.post("/quic/ack-frequency-test")
async def run_ack_frequency_test(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_ack_frequency_test(host, port)

@router.post("/quic/stateless-reset-test")
async def run_stateless_reset_test(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_stateless_reset_test(host, port)

@router.post("/quic/version-negotiation-test")
async def run_version_negotiation_test(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_version_negotiation_test(host, port)

@router.post("/quic/crypto-reassembly-test")
async def run_crypto_reassembly_test(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_crypto_stream_reassembly_test(host, port)

@router.post("/quic/multipath-quic-test")
async def run_multipath_quic_test(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_multipath_quic_test(host, port)

@router.post("/quic/webtransport-protocol-test")
async def run_webtransport_protocol_test(payload: Dict[str, Any]):
    host, port = _extract_target(payload)
    return await adv_quic_engine_instance.run_webtransport_protocol_test(host, port)

from app.agent.mesh import agent_mesh_instance
from app.core.assertions import assertion_engine_instance
from app.core.ai_diag import ai_diag_instance

@router.get("/agents/mesh")
async def list_agent_mesh():
    return agent_mesh_instance.list_agents()

@router.post("/agents/mesh/benchmark")
async def run_mesh_benchmark(payload: Dict[str, Any]):
    target = payload.get("target_host", "cloudflare-quic.com")
    return await agent_mesh_instance.execute_multi_region_benchmark(target)

@router.post("/assertions/evaluate")
async def evaluate_assertions(payload: Dict[str, Any]):
    result = payload.get("result", {})
    rules = payload.get("assertions", [])
    return assertion_engine_instance.evaluate_assertions(result, rules)

from app.protocols.openssl_advanced import adv_openssl_engine_instance

@router.post("/openssl/full-audit")
async def run_openssl_full_audit(payload: Dict[str, Any]):
    url = payload.get("target_url", "cloudflare.com")
    port = int(payload.get("port", 443))
    return adv_openssl_engine_instance.run_full_openssl_audit(url, port)

from app.protocols.quic_injector import quic_injector_instance

@router.post("/quic/inject/params")
async def run_quic_inject_params(payload: Dict[str, Any]):
    host = payload.get("host", "quic.tech")
    port = int(payload.get("port", 4433))
    params = payload.get("params", {})
    return await quic_injector_instance.inject_transport_parameters(host, port, params)

@router.post("/quic/inject/frame")
async def run_quic_inject_frame(payload: Dict[str, Any]):
    host = payload.get("host", "quic.tech")
    port = int(payload.get("port", 4433))
    frame_type = payload.get("frame_type", "RESET_STREAM")
    stream_id = int(payload.get("stream_id", 4))
    error_code = int(payload.get("error_code", 10))
    max_data_limit = int(payload.get("max_data_limit", 1048576))
    payload_text = payload.get("payload_text", "")
    return await quic_injector_instance.inject_custom_frame(host, port, frame_type, stream_id, error_code, max_data_limit, payload_text)

@router.post("/quic/inject/fault")
async def run_quic_inject_fault(payload: Dict[str, Any]):
    host = payload.get("host", "quic.tech")
    port = int(payload.get("port", 4433))
    fault_type = payload.get("fault_type", "BIT_FLIP_HEADER_TYPE")
    return await quic_injector_instance.inject_fault_corruption(host, port, fault_type)

from app.protocols.quic_performance import quic_perf_engine_instance

@router.post("/quic/perf/autotune-bdp")
async def run_quic_autotune_bdp(payload: Dict[str, Any]):
    rtt = float(payload.get("rtt_ms", 25.0))
    bw = float(payload.get("bandwidth_mbps", 100.0))
    return quic_perf_engine_instance.autotune_flow_control_bdp(rtt, bw)

@router.post("/quic/perf/gso-benchmark")
async def run_quic_gso_benchmark():
    return quic_perf_engine_instance.benchmark_udp_gso_offload()

@router.get("/quic/perf/pool-status")
async def get_quic_pool_status():
    return quic_perf_engine_instance.get_pool_status()







