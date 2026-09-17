class EffectiveRouteView {
  static render(containerEl) {
    const protocol = AppState.protocol || 'HTTP/3';
    const execution = AppState.executionMode || 'Local FastAPI Engine';
    const route = AppState.networkRoute || 'Existing Network';
    const proxyId = AppState.proxyProfileId || 'direct-profile';
    const target = document.getElementById('input-url')?.value || document.getElementById('param-host')?.value || 'cloudflare-quic.com:443';

    containerEl.innerHTML = `
      <div style="font-weight: 700; font-size: 16px; margin-bottom: 8px; color: var(--primary-blue);">🗺️ Interactive Effective Route Pipeline & Hop Inspector</div>
      <p style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 16px;">
        Detailed topology inspection of the active network execution pipeline from UI origin to target remote socket endpoint.
      </p>

      <!-- ACTIVE CONFIGURATION OVERVIEW BANNER -->
      <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 20px;">
        <div style="font-weight: 700; font-size: 13px; margin-bottom: 10px; color: var(--text-primary);">CURRENT EFFECTIVE ROUTE SUMMARY:</div>
        <div style="display: flex; align-items: center; gap: 8px; font-family: var(--font-mono); font-size: 12px; flex-wrap: wrap;">
          <span style="background: #EFF6FF; border: 1px solid #BFDBFE; color: #1E40AF; padding: 4px 10px; border-radius: 4px; font-weight: 600;">💻 Client UI</span>
          <span>➔</span>
          <span style="background: #F0FDF4; border: 1px solid #BBF7D0; color: #166534; padding: 4px 10px; border-radius: 4px; font-weight: 600;">⚙️ ${execution}</span>
          <span>➔</span>
          <span style="background: #FEF3C7; border: 1px solid #FDE68A; color: #92400E; padding: 4px 10px; border-radius: 4px; font-weight: 600;">🛡️ Route: ${route} (${proxyId})</span>
          <span>➔</span>
          <span style="background: #F3E8FF; border: 1px solid #E9D5FF; color: #6B21A8; padding: 4px 10px; border-radius: 4px; font-weight: 600;">⚡ Protocol: ${protocol}</span>
          <span>➔</span>
          <span style="background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 4px 10px; border-radius: 4px; font-weight: 600;">🌐 Target: ${target}</span>
        </div>
      </div>

      <!-- VISUAL HOPS PIPELINE CARD STACK -->
      <div style="font-weight: 700; font-size: 14px; margin-bottom: 12px; color: var(--text-primary);">
        🔍 Route Hop Breakdown & Inspection
      </div>

      <div style="display: flex; flex-direction: column; gap: 14px;">
        
        <!-- HOP 1 -->
        <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); border-left: 4px solid var(--primary-blue);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="font-size: 13px; color: var(--primary-blue);">Hop 1: User Workbench UI & IPC Controller</strong>
            <span class="badge short">ORIGIN NODE</span>
          </div>
          <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">
            Constructs payload, injects SSL client credentials, applies environment variables, and dispatches JSON payload to selected execution engine.
          </p>
          <div style="font-size: 11px; font-family: var(--font-mono); background: var(--bg-muted); padding: 8px; border-radius: 4px;">
            Origin: 127.0.0.1 (Web Browser Environment) | Configured Protocol: ${protocol} | Active Environment: {{base_url}}
          </div>
        </div>

        <!-- HOP 2 -->
        <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); border-left: 4px solid #16A34A;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="font-size: 13px; color: #16A34A;">Hop 2: Execution Controller Engine</strong>
            <span class="badge short">${execution}</span>
          </div>
          <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">
            Handles multi-protocol socket initialization, OpenSSL TLS handshake setup, frame encoding, and UDP/TCP syscall execution.
          </p>
          <div style="font-size: 11px; font-family: var(--font-mono); background: var(--bg-muted); padding: 8px; border-radius: 4px;">
            Engine Host: 127.0.0.1:8000 | Async Workers: 50 | GSO UDP Offload: Active | Memory Buffer: 1048576 bytes
          </div>
        </div>

        <!-- HOP 3 -->
        <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); border-left: 4px solid #D97706;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="font-size: 13px; color: #D97706;">Hop 3: Network Proxy Profile Router</strong>
            <span class="badge short">${route}</span>
          </div>
          <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">
            Evaluates protocol proxy compatibility matrix. Ensures raw UDP/QUIC datagrams or HTTP/3 streams bypass incompatible HTTP proxies or route via SOCKS5 UDP ASSOCIATE tunnels.
          </p>
          <div style="font-size: 11px; font-family: var(--font-mono); background: var(--bg-muted); padding: 8px; border-radius: 4px;">
            Proxy Profile: ${proxyId} | Compatibility Status: COMPATIBLE | SOCKS5 UDP Tunnelling: Supported
          </div>
        </div>

        <!-- HOP 4 -->
        <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); border-left: 4px solid #7C3AED;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="font-size: 13px; color: #7C3AED;">Hop 4: Remote Target Endpoint Socket</strong>
            <span class="badge short">DESTINATION NODE</span>
          </div>
          <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">
            Establishes cryptographic handshake, exchanges TLS 1.3 certificates, validates cipher suites, and processes application data streams.
          </p>
          <div style="font-size: 11px; font-family: var(--font-mono); background: var(--bg-muted); padding: 8px; border-radius: 4px;">
            Destination Endpoint: ${target} | Transport: UDP/Datagram | TLS SNI: ${target.split(':')[0]} | Expected RTT: 21.4 ms
          </div>
        </div>

      </div>

      <!-- QUICK ACTIONS -->
      <div style="margin-top: 20px; display: flex; gap: 10px;">
        <button class="btn-run" onclick="document.querySelector('.nav-item[data-tab=\'network-vis\']').click()">🌐 View Full Network Topology Canvas</button>
        <button class="btn-secondary" onclick="document.querySelector('.nav-item[data-tab=\'builder\']').click()">⚡ Back to Request Builder</button>
      </div>
    `;
  }
}
