class OverviewGuideView {
  static render(containerEl) {
    containerEl.innerHTML = `
      <div style="max-width: 900px; margin: 0 auto; padding: 10px 0;">
        
        <!-- WELCOME BANNER -->
        <div style="background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%); border: 1px solid #BFDBFE; padding: 20px; border-radius: 8px; margin-bottom: 24px;">
          <h2 style="color: #1E40AF; margin-bottom: 8px; font-size: 20px; display: flex; align-items: center; gap: 8px;">
            👋 Welcome to QUICLAB Workbench
          </h2>
          <p style="color: #1E3A8A; font-size: 13px; line-height: 1.6;">
            QUICLAB is a Postman-like multi-protocol network testing platform designed for inspecting, debugging, and benchmarking network protocols across <strong>HTTP/1.1, HTTP/2, HTTP/3, Raw QUIC, Raw TCP, Raw UDP, WebSocket, DNS, FTP, SSH, SFTP, RTP, MoQ, and WebTransport</strong>.
          </p>
        </div>

        <!-- 3 CORE CONCEPTS DIAGRAM -->
        <h3 style="font-size: 15px; margin-bottom: 14px; color: var(--text-primary);">Understanding QUICLAB's 3 Core Concepts</h3>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 28px;">
          
          <div style="background: var(--bg-surface); padding: 16px; border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="font-size: 14px; font-weight: 700; color: var(--primary-blue); margin-bottom: 6px;">1. Protocol</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px;">What are you testing?</div>
            <p style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
              Choose between high-level web protocols (HTTP/1, HTTP/2, HTTP/3, WebSocket) or raw socket engines (Raw QUIC, TCP, UDP, DNS). Each has dynamic form options.
            </p>
          </div>

          <div style="background: var(--bg-surface); padding: 16px; border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="font-size: 14px; font-weight: 700; color: #7C3AED; margin-bottom: 6px;">2. Execution Mode</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px;">Where does the test run?</div>
            <p style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
              Execute tests directly on your <strong>Local Machine</strong> or remotely via a <strong>QUICLAB Agent</strong> daemon running on a server, VM, or lab environment (e.g. <code>127.0.0.1:9000</code>).
            </p>
          </div>

          <div style="background: var(--bg-surface); padding: 16px; border-radius: 8px; border: 1px solid var(--border-color);">
            <div style="font-size: 14px; font-weight: 700; color: #059669; margin-bottom: 6px;">3. Network Route</div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px;">How traffic leaves?</div>
            <p style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
              Route traffic via <strong>Existing Network</strong> (Direct OS stack) or a <strong>Configured Proxy</strong> (SOCKS5, HTTP, HTTPS). Incompatible proxies (like QUIC over HTTP Proxy) are flagged instantly.
            </p>
          </div>

        </div>

        <!-- QUICKSTART WORKFLOW STEPS -->
        <h3 style="font-size: 15px; margin-bottom: 14px; color: var(--text-primary);">Quickstart Workflow: How to use QUICLAB in 4 Steps</h3>
        
        <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 28px;">
          
          <div style="display: flex; gap: 14px; background: var(--bg-surface); padding: 14px; border-radius: 6px; border-left: 4px solid var(--primary-blue);">
            <div style="background: var(--primary-blue); color: #FFF; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; flex-shrink: 0;">1</div>
            <div>
              <strong style="font-size: 13px;">Select Protocol & Target Endpoint</strong>
              <p style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                In <strong>⚡ Request Builder</strong>, pick a protocol (e.g. <code>HTTP/3</code> or <code>Raw QUIC</code>) and enter your target URL or Host/Port (e.g., <code>https://cloudflare-quic.com/</code> or <code>quic.tech:4433</code>).
              </p>
            </div>
          </div>

          <div style="display: flex; gap: 14px; background: var(--bg-surface); padding: 14px; border-radius: 6px; border-left: 4px solid #7C3AED;">
            <div style="background: #7C3AED; color: #FFF; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; flex-shrink: 0;">2</div>
            <div>
              <strong style="font-size: 13px;">Set Execution & Network Route</strong>
              <p style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                Use the Top Navbar dropdowns to select <strong>Local</strong> or <strong>Agent</strong> mode, and check the <strong>Effective Route Preview</strong> diagram at the bottom of the form.
              </p>
            </div>
          </div>

          <div style="display: flex; gap: 14px; background: var(--bg-surface); padding: 14px; border-radius: 6px; border-left: 4px solid #16A34A;">
            <div style="background: #16A34A; color: #FFF; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; flex-shrink: 0;">3</div>
            <div>
              <strong style="font-size: 13px;">Execute Transaction</strong>
              <p style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                Click <strong>▶ Run Request</strong> to execute the protocol test. Toggle between <strong>JSON / Raw</strong> data and <strong>🌐 Web View (Rendered HTML)</strong> to see the output.
              </p>
            </div>
          </div>

          <div style="display: flex; gap: 14px; background: var(--bg-surface); padding: 14px; border-radius: 6px; border-left: 4px solid #D97706;">
            <div style="background: #D97706; color: #FFF; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; flex-shrink: 0;">4</div>
            <div>
              <strong style="font-size: 13px;">Inspect Deep Protocols & Network Parameters</strong>
              <p style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                Use the left sidebar tabs:
                • <strong>📦 QUIC Packet Inspector</strong> to analyze frames (ACK, CRYPTO, STREAM, MAX_DATA).<br>
                • <strong>🌳 QUIC Stream Visualizer</strong> to see active streams.<br>
                • <strong>🔗 Cross-Layer Correlation</strong> to trace HTTP/3 ➔ Stream ➔ Packet ➔ UDP.<br>
                • <strong>🧪 Network Laboratory</strong> to test latency/loss or Wi-Fi ➔ 5G connection migration.
              </p>
            </div>
          </div>

        </div>

      </div>
    `;
  }
}
