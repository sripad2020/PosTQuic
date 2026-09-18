import sqlite3
import json
import os
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "quiclab.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Collections table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS collections (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        variables TEXT DEFAULT '{}'
    )
    """)
    
    # Requests table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        id TEXT PRIMARY KEY,
        collection_id TEXT,
        name TEXT NOT NULL,
        protocol TEXT NOT NULL,
        config TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(collection_id) REFERENCES collections(id) ON DELETE CASCADE
    )
    """)
    
    # Proxy profiles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proxy_profiles (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        proxy_type TEXT NOT NULL,
        host TEXT NOT NULL,
        port INTEGER NOT NULL,
        auth_type TEXT DEFAULT 'None',
        username TEXT,
        password_encrypted TEXT,
        tls_config TEXT DEFAULT '{}',
        bypass_rules TEXT DEFAULT '[]',
        is_default INTEGER DEFAULT 0
    )
    """)
    
    # Environments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS environments (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        variables TEXT NOT NULL,
        is_active INTEGER DEFAULT 0
    )
    """)
    
    # Sessions History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        protocol TEXT NOT NULL,
        target TEXT NOT NULL,
        execution_mode TEXT DEFAULT 'Local',
        state TEXT DEFAULT 'CLOSED',
        rtt_ms REAL DEFAULT 0.0,
        timestamp TEXT NOT NULL,
        details TEXT DEFAULT '{}'
    )
    """)

    # Test Results / Saved Captures
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS captures (
        id TEXT PRIMARY KEY,
        request_name TEXT,
        protocol TEXT,
        execution_mode TEXT,
        network_route TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        summary TEXT,
        packets TEXT,
        metrics TEXT
    )
    """)
    
    conn.commit()
    
    # Seed default values if empty
    cursor.execute("SELECT COUNT(*) FROM proxy_profiles")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO proxy_profiles (id, name, proxy_type, host, port, auth_type, is_default)
        VALUES ('direct-profile', 'Direct (No Proxy)', 'Direct', 'localhost', 0, 'None', 1),
               ('corp-socks5', 'Corporate SOCKS5 Proxy', 'SOCKS5', '192.168.1.100', 1080, 'Username/Password', 0),
               ('corp-http', 'Corporate HTTP Proxy', 'HTTP Proxy', 'proxy.corp.internal', 8080, 'None', 0)
        """)
        
    cursor.execute("SELECT COUNT(*) FROM environments")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO environments (id, name, variables, is_active)
        VALUES ('dev-env', 'Development', '{"base_url": "http://127.0.0.1:8000", "quic_target": "quic.tech:4433", "proxy_host": "10.0.0.1", "auth_token": "bearer_dev_99182"}', 1),
               ('staging-env', 'Staging Lab', '{"base_url": "https://staging.quiclab.io", "quic_target": "staging.quiclab.io:443", "proxy_host": "192.168.1.100", "auth_token": "bearer_stage_44210"}', 0),
               ('prod-env', 'Production QUIC Cloud', '{"base_url": "https://cloudflare-quic.com", "quic_target": "cloudflare-quic.com:443", "proxy_host": "10.200.0.1", "auth_token": "bearer_prod_sec77"}', 0)
        """)
        
    cursor.execute("SELECT COUNT(*) FROM collections")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO collections (id, name, description, variables)
        VALUES ('col-1', 'QUIC & HTTP/3 Research Suite', 'Automated test suite for testing 0-RTT, QPACK compression, stream multiplexing, and HTTP/3 performance', '{"target": "cloudflare-quic.com"}'),
               ('col-2', 'Multi-Protocol Benchmark', 'Raw TCP, UDP, WebSocket, DNS resolution, and FTP file transfer regression test suite', '{"dns_server": "1.1.1.1"}'),
               ('col-3', 'TLS & OpenSSL Security Audit', '15-Point OpenSSL diagnostic audit, SSL handshake trace, and certificate validation suite', '{"target": "google.com"}')
        """)

    cursor.execute("SELECT COUNT(*) FROM sessions")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO sessions (id, session_id, protocol, target, execution_mode, state, rtt_ms, timestamp)
        VALUES 
        ('s_001', 's_081a2f', 'HTTP/3', 'https://cloudflare-quic.com/', 'Local FastAPI Engine', 'CLOSED', 21.4, '10:14:02'),
        ('s_002', 's_77b31c', 'RAW QUIC', 'quic.tech:4433', 'Local FastAPI Engine', 'CLOSED', 19.8, '10:11:45'),
        ('s_003', 's_39c11a', 'WEBSOCKET', 'wss://echo.websocket.events', 'Local FastAPI Engine', 'CLOSED', 14.2, '09:55:12'),
        ('s_004', 's_92d40e', 'OPENSSL', 'cloudflare.com:443', 'Local FastAPI Engine', 'CLOSED', 25.1, '09:40:00')
        """)
        
    conn.commit()
    conn.close()

# Helper Functions
def add_session_record(session_id: str, protocol: str, target: str, execution_mode: str = "Local", state: str = "CLOSED", rtt_ms: float = 21.4, timestamp: str = "Just now", details: str = "{}"):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO sessions (id, session_id, protocol, target, execution_mode, state, rtt_ms, timestamp, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (f"s_{os.urandom(4).hex()}", session_id, protocol, target, execution_mode, state, rtt_ms, timestamp, details))
    conn.commit()
    conn.close()

def clear_all_sessions():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()

# Run initialization on import
init_db()



