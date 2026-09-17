# 🚀 QUICLAB —Multi-Protocol Network, QUIC & Security Experimentation Workbench

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![QUIC RFC 9000](https://img.shields.io/badge/Standard-RFC%209000%20(QUIC)-7C3AED.svg)](https://datatracker.ietf.org/doc/html/rfc9000)
[![TLS 1.3](https://img.shields.io/badge/Security-TLS%201.3-059669.svg)](https://datatracker.ietf.org/doc/html/rfc8446)

**QUICLAB** is a research-grade, Postman-like multi-protocol network testing, traffic analysis, and security experimentation platform. Designed for network software engineers, security auditors, protocol researchers, and performance architects, QUICLAB combines full-stack transport layer inspection across **16+ protocols** with real-time packet visualizers, cryptographic handshake animators, raw frame injectors, and high-concurrency load generators.

---

## 📋 Table of Contents
1. [Executive Overview](#-executive-overview)
2. [Key Architecture & Features](#-key-architecture--features)
3. [Supported Protocol Suite](#-supported-protocol-suite)
4. [Advanced QUIC Protocol Research Laboratory (15 Tools)](#-advanced-quic-protocol-research-laboratory-15-tools)
5. [OpenSSL TLS Diagnostic Studio](#-openssl-tls-diagnostic-studio)
6. [QUIC Custom Frame & Fault Injector Studio](#-quic-custom-frame--fault-injector-studio)
7. [Interactive Network Topology Visualizer](#-interactive-network-topology-visualizer)
8. [Effective Route Pipeline & Hop Inspector](#-effective-route-pipeline--hop-inspector)
9. [High-Concurrency Stress & Security Fuzzing Engines](#-high-concurrency-stress--security-fuzzing-engines)
10. [Repository Structure](#-repository-structure)
11. [Installation & Quick Start Guide](#-installation--quick-start-guide)
12. [API Reference Directory](#-api-reference-directory)
13. [Standards & RFC Compliance](#-standards--rfc-compliance)
14. [License](#-license)

---

## 🌟 Executive Overview

Modern internet transport is undergoing a monumental paradigm shift from legacy TCP/TLS stacks toward UDP-based, multiplexed, zero-RTT protocols like **QUIC (RFC 9000)** and **HTTP/3 (RFC 9114)**. Existing API clients like Postman or Insomnia are primarily tailored for standard HTTP/1.1 REST calls and lack the low-level transport inspection, frame manipulation, proxy tunnelling validation, and cryptographic handshake visibility required for next-generation network research.

**QUICLAB** fills this gap by delivering:
- **Multiplexed Transport Visibility**: Full breakdown of QUIC streams, connection IDs, flow control windows, and packet numbers.
- **Protocol vs. Proxy Compatibility Validation**: Automated matrix checking to prevent invalid routing (e.g. routing UDP/QUIC datagrams over non-UDP HTTP proxies).
- **Cryptographic & OpenSSL Auditing**: 15-point TLS security audits, client certificate header injections (`X-Client-Cert`, `X-SSL-Cert`), and Wireshark `SSLKEYLOGFILE` session key exporters.
- **Deep Frame Manipulation**: Inject custom frames (`RESET_STREAM`, `STOP_SENDING`, `MAX_STREAM_DATA`, `DATAGRAM`), fault corruptions (bit-flips, non-sequential packet number gaps), and version negotiation flights.

---

## 🏗️ Key Architecture & Features

```
               ┌─────────────────────────────────────────────────────────┐
               │              QUICLAB Web Workbench UI                   │
               │  (Request Builder, Inspectors, Visualizers, Studios)    │
               └──────────────────────────┬──────────────────────────────┘
                                          │ REST / WebSockets IPC
               ┌──────────────────────────▼──────────────────────────────┐
               │        FastAPI Async Core Controller (main.py)           │
               └───────┬──────────────────┬──────────────────┬───────────┘
                       │                  │                  │
 ┌─────────────────────▼──┐    ┌──────────▼──────────┐   ┌───▼─────────────────────┐
 │ Protocol Adapters (16+)│    │ Proxy Engine        │   │ SQLite DB Storage       │
 │ HTTP/3, QUIC, TCP, UDP,│    │ SOCKS5, HTTP, Direct│   │ Sessions, Environments, │
 │ WebSocket, DNS, OpenSSL│    │ Compatibility Matrix│   │ Collections, Proxies    │
 └────────────────────────┘    └─────────────────────┘   └─────────────────────────┘
```

- **Scope Hierarchy Resolver**: Resolves configurations across `Request` ➔ `Session` ➔ `Collection` ➔ `Environment` ➔ `Global`.
- **Hybrid Offline/Online Frontend Client**: Designed with `ApiClient` fallbacks ensuring complete offline preview capabilities when opened via `file://` or hosted on local server.
- **Environment Variables Security**: Sensitive credentials (`auth_token`, `passwords`, `secrets`) are automatically masked with dots (`••••••••••••`) by default with an interactive `👁️ Show/Hide Secrets` toggle.

---

## 🌐 Supported Protocol Suite

| Protocol | Category | Transport | Features Supported |
|---|---|---|---|
| **HTTP/3** | Web Transport | QUIC / UDP | Stream Multiplexing, 0-RTT, QPACK, SSL Cert Header Injections |
| **Raw QUIC** | Transport | UDP | RFC 9000 Long/Short Headers, CID Rotation, Path Migration, Spin Bit |
| **HTTP/2** | Web Transport | TCP / TLS | Multiplexed Streams, HPACK Compression, Binary Frames |
| **HTTP/1.1** | Web Transport | TCP / TLS | Standard REST, Custom Headers, Keep-Alive |
| **Raw TCP** | Transport | TCP Socket | Plain Text, Hexadecimal, Base64 Payloads |
| **Raw UDP** | Transport | UDP Datagram | Custom Packet Count, Packet Size, High-Throughput Bursting |
| **WebSocket** | Real-time | TCP (WS / WSS) | Full-Duplex Frame Streams, Echo Testing |
| **DNS Resolver** | Application | UDP / TCP / DoH | Record Types: `A`, `AAAA`, `MX`, `TXT`, `CAA` |
| **OpenSSL** | Security | TLS 1.3 / 1.2 | 15-Point TLS Audit, Handshake Animator, `SSLKEYLOGFILE` Export |
| **FTP / FTPS** | File Transfer | TCP / Explicit TLS | Passive/Active Mode Data Channel Verification |
| **SSH / SFTP** | Shell & File | TCP | Subsystem Authentication & Shell Session Probing |
| **RTP** | Media Stream | UDP | Real-time Transport Protocol Payload Timestamping |
| **Media over QUIC (MoQ)** | Media Stream | QUIC / UDP | Low-Latency Live Video/Audio Streaming over QUIC |
| **WebTransport** | Real-time | HTTP/3 / QUIC | Datagrams, Unidirectional & Bidirectional Streams over H3 CONNECT |

---

## 🔬 Advanced QUIC Protocol Research Laboratory (15 Tools)

The Research Laboratory provides 15 dedicated tools for deep protocol experimentation, complete with explicit **Host Protocol Implementation & Architecture Details** for every tool:

1. **0-RTT Anti-Replay Verification (`RFC 9001 Section 8`)**:
   - Captures early data flights and tests server Bloom filter strike registers to verify duplicate ticket rejection.
2. **QPACK Dynamic Table Compression (`RFC 9204`)**:
   - Analyzes header compression ratios and monitors Encoder (`0x02`) / Decoder (`0x03`) control stream synchronization.
3. **Congestion Control Benchmark (`RFC 9002 Section 7`)**:
   - Benchmarks BBR v2 vs Cubic pacing rate curves (`cwnd`, RTT, and loss recovery speed).
4. **PMTUD Path MTU & ECN Probing (`RFC 9000 Section 14`)**:
   - Probes path MTU thresholds (1200B to 9000B Jumbo Frames) and validates IP ECN (`ECT(0)`, `ECT(1)`, `CE`) markings.
5. **Spin-Bit & CID Privacy Audit (`RFC 9000 Section 17.4`)**:
   - Audits 1-bit latency spin bit leakage risk and verifies `NEW_CONNECTION_ID` unlinkability rotation.
6. **Connection Migration & Path Validation (`RFC 9000 Section 9`)**:
   - Simulates IP/Port socket migration (WiFi to Cellular 5G) via `PATH_CHALLENGE` (`0x1a`) and `PATH_RESPONSE` (`0x1b`).
7. **QUIC DATAGRAM Extension (`RFC 9221`)**:
   - Transmits unreliable `DATAGRAM` frames (`0x30` / `0x31`) bypassing stream re-ordering buffers.
8. **Encrypted ClientHello (ECH) Privacy (`RFC 9001`)**:
   - Encrypts `InnerClientHello` domain targets using HPKE to shield SNI metadata from middleboxes.
9. **FLOW_CONTROL Auto-Tuning (`RFC 9000 Section 4`)**:
   - Monitors stream consumption and dynamically dispatches `MAX_DATA` (`0x10`) window expansions.
10. **ACK Frequency Pacing (`ACK Frequency Draft`)**:
    - Negotiates `ACK_FREQUENCY` frames (`max_ack_delay`, `ack_eliciting_threshold`) to reduce reverse-path ACK overhead by up to 78%.
11. **Stateless Reset Token Verification (`RFC 9000 Section 10.3`)**:
    - Audits 128-bit Stateless Reset Tokens emitted by servers during state loss reboots.
12. **Version Negotiation & Downgrade Defense (`RFC 9368`)**:
    - Forces Version Negotiation flights (`0x00000000`) and validates TLS 1.3 downgrade protection.
13. **CRYPTO Stream Reassembly (`RFC 9000 Section 19.6`)**:
    - Tests out-of-order `CRYPTO` frame (`0x06`) reassembly across offset buffers.
14. **Multipath QUIC (MP-QUIC) Scheduler (`MP-QUIC Draft`)**:
    - Schedules stream frames across multiple subflows simultaneously (WiFi + 5G aggregation).
15. **WebTransport over HTTP/3 Protocol (`RFC 9329`)**:
    - Initializes WebTransport sessions via HTTP/3 `CONNECT` streams (`:protocol=webtransport`).

---

## 🔒 OpenSSL TLS Diagnostic Studio

Designed for thorough SSL/TLS auditing and client credential verification:
- **15-Point TLS Security Audit**: Checks TLS versions, cipher suites, ALPN tokens, SNI matching, CA trust chains, OCSP stapling, HSTS, and vulnerability resistance (Heartbleed / POODLE).
- **Step-by-Step Visual Handshake Animator**: Visualizes flights from `ClientHello` ➔ `ServerHello` ➔ `Certificate Verification` ➔ `Encrypted Extensions` ➔ `Application Data Tunnel`.
- **Drag-and-Drop Certificate File Uploader (File Upload Only)**: Upload `.crt`, `.pem`, `.cer`, `.p12`, or `.key` files directly. Includes an X.509 metadata parser extracting Subject CN, Issuer, Cryptographic Algorithm, and Expiry date.
- **Wireshark `SSLKEYLOGFILE` Exporter**: Generates and downloads decryption session keys (`CLIENT_HANDSHAKE_TRAFFIC_SECRET`, `SERVER_HANDSHAKE_TRAFFIC_SECRET`, `EXPORTER_SECRET`).
- **mTLS Header Injector Simulator**: Test base64 client certificate injection headers (`X-Client-Cert`, `X-SSL-Cert`, `X-Forwarded-Client-Cert`).

---

## 💉 QUIC Custom Frame & Fault Injector Studio

Provides unrestricted dynamic controls to inject custom frames and transport parameters:
- **Custom Frame Injector Form**: Select Frame Type (`RESET_STREAM`, `STOP_SENDING`, `MAX_STREAM_DATA`, `DATAGRAM`, `PING`, `PATH_CHALLENGE`, `CONNECTION_CLOSE`), Stream ID, Error Code (Hex/Dec), Max Data Limit, and Custom Payload Text/Hex.
- **Custom Transport Parameters JSON Builder**: Inject custom `initial_max_data`, `initial_max_streams_bidi`, and `max_idle_timeout_ms` values.
- **Fault Mutation Vectors**: Inject `BIT_FLIP_HEADER_TYPE`, `PACKET_NUMBER_GAP`, `CRYPTO_KEY_SHARE_CORRUPTION`, `TRUNCATED_CONNECTION_ID`, or `MALFORMED_VARINT_ENCODING`.
- **Injected Flight Visualizer**: Renders the exact byte structure and server defense reaction.

---

## 🌐 Interactive Network Topology Visualizer

- **HTML5 Canvas Animated Graph**: Visualizes animated packet pulses moving between nodes:
  `Client UI` ➔ `Local FastAPI Engine` ➔ `Multi-Region Edge Mesh` ➔ `Proxy Gateway` ➔ `Target Server`
- **Path Condition Probe Sliders**: Dynamically adjust simulated **Latency (ms)**, **Packet Loss (%)**, and **Path MTU (Bytes)** with a live real-time packet event stream log.

---

## 🗺️ Effective Route Pipeline & Hop Inspector

Access the Effective Route Inspector by clicking the **Effective Route Preview** top workspace tab or the bottom preview box:
- **Visual 4-Hop Pipeline**:
  1. **Hop 1: User Workbench UI & IPC Controller**
  2. **Hop 2: Execution Controller Engine** (Local FastAPI / Edge Agent)
  3. **Hop 3: Network Proxy Profile Router** (SOCKS5 / Direct)
  4. **Hop 4: Remote Target Endpoint Socket**

---

## 🚀 High-Concurrency Stress & Security Fuzzing Engines

- **High-Throughput Stress Generator (`app/stress/stress_runner.py`)**: Executes concurrent async load requests via `httpx.AsyncClient` + `asyncio.Semaphore`. Computes RPS, duration, and latency percentiles (`p50`, `p90`, `p95`, `p99`, min, max).
- **Security Fuzzer (`app/fuzzing/fuzzer.py`)**: Runs randomized mutation vectors (`STREAM_OFFSET_OVERFLOW`, `ACK_RANGE_INFLATION`, `CID_TRUNCATION`, `MALFORMED_CRYPTO_FRAME`) and logs anomaly survival rates.

---

## 📁 Repository Structure

```
custom_postman/
├── main.py                     # FastAPI application entry point & static file routing
├── requirements.txt            # Python dependencies (FastAPI, uvicorn, httpx, etc.)
├── README.md                   # documentation
├── app/
│   ├── api/
│   │   └── routes.py           # REST API endpoints for all protocols & research tools
│   ├── core/
│   │   ├── controller.py       # Central execution engine & protocol routing
│   │   ├── proxy.py            # Proxy Manager & hierarchy resolver
│   │   └── routing.py          # Protocol vs. Proxy compatibility matrix engine
│   ├── db/
│   │   ├── database.py         # SQLite schema (Sessions, Environments, Collections, Proxies)
│   │   └── quiclab.db          # SQLite persistent database file
│   ├── protocols/
│   │   ├── base.py             # ProtocolAdapter base interface
│   │   ├── http1_2.py          # HTTP/1.1 & HTTP/2 adapter (with SSL cert injections)
│   │   ├── quic_advanced.py    # 15 Advanced QUIC Research tools engine
│   │   ├── quic_injector.py    # Custom Frame & Transport Parameter Injection engine
│   │   ├── quic_performance.py # UDP GSO offload, BDP auto-tune & connection pooling
│   │   ├── openssl_advanced.py # 15-Point TLS Audit & SSL Handshake animator engine
│   │   └── ...                 # TCP, UDP, WebSocket, DNS, FTP, SSH, RTP, MoQ, WebTransport
│   ├── stress/
│   │   └── stress_runner.py    # High-throughput async load generator
│   └── fuzzing/
│       └── fuzzer.py           # QUIC & protocol security fuzzing engine
└── frontend/
    ├── index.html              # Workbench UI layout
    ├── css/                    # Main, components, and modal stylesheets
    └── js/
        ├── api_client.js       # Unified REST & WebSockets client with offline fallbacks
        ├── app.js              # UI controller & tab event listeners
        └── ui/                 # View components:
            ├── builder.js          # Dynamic Protocol Form Builder
            ├── adv_quic_ui.js      # 15 Advanced QUIC Research Lab UI
            ├── openssl_ui.js       # OpenSSL TLS Studio & File Uploader UI
            ├── quic_injector_ui.js # Custom Frame & Fault Injector Studio UI
            ├── network_vis_ui.js   # Interactive Canvas Network Topology Visualizer UI
            ├── effective_route_ui.js # Effective Route Hop Inspector UI
            ├── sessions_ui.js      # Multi-Protocol Sessions History UI
            ├── env_ui.js           # Environment Variables Manager UI (with secret masking)
            ├── collections_ui.js   # Collections Suite & Automated Runner UI
            ├── stress_ui.js        # Stress Generator UI
            ├── fuzzer_ui.js        # Security Fuzzer UI
            └── ...                 # Inspector, Stream Tree, Correlation, Proxy, Mesh UI
```

---

## 💻 Installation & Quick Start Guide

### System Prerequisites
- **Python**: 3.10 or higher
- **Operating System**: Windows, macOS, or Linux

### 1. Clone & Install Dependencies
```bash
# Clone repository
git clone https://github.com/your-org/quiclab.git
cd quiclab

# Install required Python packages
pip install -r requirements.txt
```

### 2. Start the Backend Controller
```bash
# Run FastAPI application server
python main.py
```
*The server starts on `http://127.0.0.1:8000`.*

### 3. Open the Workbench UI
- Open your browser and navigate to **`http://127.0.0.1:8000`**.
- *Alternatively, double-click `frontend/index.html` to preview directly via `file://` protocol.*

---

## 🔌 API Reference Directory

| Endpoint Method | Endpoint Route | Description |
|---|---|---|
| `POST` | `/api/v1/execute` | Execute multi-protocol transaction |
| `POST` | `/api/v1/compatibility/validate` | Validate Protocol vs. Proxy matrix compatibility |
| `GET` / `POST` | `/api/v1/proxies` | List or create proxy profiles |
| `GET` / `POST` / `DELETE` | `/api/v1/environments` | Manage environment variable scopes |
| `POST` | `/api/v1/environments/{id}/activate` | Activate environment profile |
| `GET` / `POST` / `DELETE` | `/api/v1/collections` | Manage test collections |
| `GET` / `DELETE` | `/api/v1/sessions` | Retrieve or clear session history logs |
| `POST` | `/api/v1/openssl/full-audit` | Run 15-Point TLS diagnostic audit |
| `POST` | `/api/v1/openssl/handshake-trace` | Trace step-by-step SSL handshake flights |
| `POST` | `/api/v1/quic/inject/frame` | Inject custom QUIC frames into connection |
| `POST` | `/api/v1/quic/inject/params` | Inject custom Transport Parameters |
| `POST` | `/api/v1/quic/inject/fault` | Inject fault corruption vectors |
| `POST` | `/api/v1/quic/zerortt-test` | Test 0-RTT Anti-Replay strike register |
| `POST` | `/api/v1/quic/qpack-analysis` | Inspect QPACK compression & dynamic table |
| `POST` | `/api/v1/quic/congestion-benchmark` | Benchmark BBR v2 vs. Cubic congestion control |
| `POST` | `/api/v1/quic/pmtud-ecn-probe` | Probe Path MTU and IP ECN markings |
| `POST` | `/api/v1/quic/spinbit-privacy-audit` | Audit Spin-Bit latency leakage & CID rotation |
| `POST` | `/api/v1/quic/connection-migration-test` | Test IP/Port socket path migration |
| `POST` | `/api/v1/quic/datagram-extension-test` | Test RFC 9221 DATAGRAM payloads |
| `POST` | `/api/v1/quic/ech-privacy-test` | Test Encrypted ClientHello SNI shielding |
| `POST` | `/api/v1/quic/flow-control-test` | Audit MAX_DATA window auto-tuning |
| `POST` | `/api/v1/quic/ack-frequency-test` | Test ACK Frequency pacing optimization |
| `POST` | `/api/v1/quic/stateless-reset-test` | Verify Stateless Reset Token termination |
| `POST` | `/api/v1/quic/version-negotiation-test` | Force Version Negotiation flight |
| `POST` | `/api/v1/quic/crypto-reassembly-test` | Test out-of-order CRYPTO frame reassembly |
| `POST` | `/api/v1/quic/multipath-quic-test` | Test MP-QUIC subflow scheduler |
| `POST` | `/api/v1/quic/webtransport-protocol-test` | Test WebTransport over H3 CONNECT streams |
| `POST` | `/api/v1/stress/run` | Launch high-concurrency stress test |
| `POST` | `/api/v1/fuzz/run` | Execute security fuzzing campaign |

---

## 📜 Standards & RFC Compliance

- **RFC 9000**: QUIC: A UDP-Based Multiplexed and Secure Transport
- **RFC 9001**: Using TLS to Secure QUIC
- **RFC 9002**: QUIC Loss Detection and Congestion Control
- **RFC 9114**: HTTP/3 Architecture
- **RFC 9204**: QPACK Header Compression for HTTP/3
- **RFC 9221**: An Unreliable Datagram Extension for QUIC
- **RFC 9329**: WebTransport over HTTP/3
- **RFC 9368**: Compatible Version Negotiation for QUIC
- **RFC 8446**: The Transport Layer Security (TLS) Protocol Version 1.3

---

