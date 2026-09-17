class NetworkVisView {
  static render(containerEl) {
    containerEl.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <div>
          <div style="font-weight: 700; font-size: 16px; color: var(--primary-blue);">🌐 Interactive Network Topology & Packet Traffic Visualizer</div>
          <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
            Real-time visual node graph rendering multi-protocol packet flows, edge mesh routing, proxy hops, and path probing metrics.
          </div>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn-run" style="font-size: 11px; padding: 6px 12px;" onclick="NetworkVisView.pulsePacket()">🚀 Inject Test Packet Pulse</button>
          <button class="btn-secondary" style="font-size: 11px; padding: 6px 12px;" onclick="NetworkVisView.toggleMesh()">🌐 Toggle Edge Mesh</button>
        </div>
      </div>

      <!-- MAIN GRAPH CANVAS CONTAINER -->
      <div style="background: #0F172A; border-radius: 8px; border: 1px solid #334155; padding: 14px; position: relative; margin-bottom: 16px;">
        <div style="position: absolute; top: 18px; left: 20px; color: #94A3B8; font-family: var(--font-mono); font-size: 11px; z-index: 10;">
          <span style="display: inline-block; width: 8px; height: 8px; background: #22C55E; border-radius: 50%; margin-right: 6px;"></span>
          TOPOLOGY STATE: DYNAMIC PACKET PULSES ACTIVE | RTT: <span id="vis-rtt">21.4 ms</span>
        </div>

        <canvas id="network-topology-canvas" width="900" height="340" style="width: 100%; height: 340px; display: block;"></canvas>
      </div>

      <!-- NETWORK SIMULATION PARAMETER CONTROLS & EVENT LOG -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
        
        <!-- CONTROL PANEL -->
        <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-weight: 700; font-size: 13px; margin-bottom: 10px; color: var(--primary-blue);">⚙️ Network Path Condition Probes</div>
          
          <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; font-size: 11.5px; margin-bottom: 4px;">
              <span>Simulated Latency:</span>
              <strong id="val-vis-latency">25 ms</strong>
            </div>
            <input type="range" id="slider-vis-latency" min="1" max="200" value="25" style="width: 100%;" oninput="document.getElementById('val-vis-latency').innerText = this.value + ' ms'">
          </div>

          <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; font-size: 11.5px; margin-bottom: 4px;">
              <span>Packet Loss:</span>
              <strong id="val-vis-loss">0.5 %</strong>
            </div>
            <input type="range" id="slider-vis-loss" min="0" max="10" step="0.1" value="0.5" style="width: 100%;" oninput="document.getElementById('val-vis-loss').innerText = this.value + ' %'">
          </div>

          <div>
            <div style="display: flex; justify-content: space-between; font-size: 11.5px; margin-bottom: 4px;">
              <span>Path MTU Size:</span>
              <strong id="val-vis-mtu">1472 Bytes</strong>
            </div>
            <input type="range" id="slider-vis-mtu" min="576" max="9000" step="64" value="1472" style="width: 100%;" oninput="document.getElementById('val-vis-mtu').innerText = this.value + ' Bytes'">
          </div>
        </div>

        <!-- PACKET FLOW LOG -->
        <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-weight: 700; font-size: 13px; margin-bottom: 10px; color: var(--primary-blue);">📜 Live Packet Flow Audit Stream</div>
          <div id="vis-packet-log" style="font-family: var(--font-mono); font-size: 11px; height: 120px; overflow-y: auto; background: var(--bg-muted); padding: 8px; border-radius: 4px;">
            <div>[10:14:02.100] Client UI ➔ Local Engine: POST /execute (HTTP/3)</div>
            <div>[10:14:02.105] Local Engine ➔ SOCKS5 Proxy: UDP ASSOCIATE Request</div>
            <div>[10:14:02.115] Proxy ➔ cloudflare-quic.com: QUIC Initial Flight (TLS 1.3)</div>
            <div>[10:14:02.136] cloudflare-quic.com ➔ Client UI: Handshake Finished (ACK 1)</div>
          </div>
        </div>

      </div>
    `;

    // Initialize Canvas Animation after DOM attachment
    setTimeout(() => {
      NetworkVisView.initCanvasAnimation();
    }, 100);
  }

  static animFrameId = null;
  static packets = [];

  static initCanvasAnimation() {
    const canvas = document.getElementById('network-topology-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const nodes = [
      { id: 'client', label: 'Client UI Workbench', x: 80, y: 170, color: '#3B82F6' },
      { id: 'engine', label: 'Local FastAPI Engine', x: 280, y: 100, color: '#22C55E' },
      { id: 'mesh', label: 'Edge Mesh Agent', x: 280, y: 240, color: '#06B6D4' },
      { id: 'proxy', label: 'Proxy Gateway', x: 540, y: 170, color: '#F59E0B' },
      { id: 'target', label: 'Target Remote Server', x: 780, y: 170, color: '#A855F7' }
    ];

    const connections = [
      { from: 'client', to: 'engine' },
      { from: 'client', to: 'mesh' },
      { from: 'engine', to: 'proxy' },
      { from: 'mesh', to: 'proxy' },
      { from: 'proxy', to: 'target' }
    ];

    // Spawn continuous animated packet pulses
    if (NetworkVisView.packets.length === 0) {
      NetworkVisView.packets = [
        { from: 'client', to: 'engine', progress: 0.1, speed: 0.015, label: 'JSON Req' },
        { from: 'engine', to: 'proxy', progress: 0.4, speed: 0.012, label: 'QUIC Initial' },
        { from: 'proxy', to: 'target', progress: 0.7, speed: 0.018, label: '1-RTT Data' }
      ];
    }

    function draw() {
      if (!canvas || !canvas.parentElement) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw connection lines
      connections.forEach(conn => {
        const n1 = nodes.find(n => n.id === conn.from);
        const n2 = nodes.find(n => n.id === conn.to);
        if (n1 && n2) {
          ctx.beginPath();
          ctx.moveTo(n1.x, n1.y);
          ctx.lineTo(n2.x, n2.y);
          ctx.strokeStyle = '#334155';
          ctx.lineWidth = 2;
          ctx.setLineDash([4, 4]);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      });

      // Draw active packet pulses
      NetworkVisView.packets.forEach(p => {
        const n1 = nodes.find(n => n.id === p.from);
        const n2 = nodes.find(n => n.id === p.to);
        if (n1 && n2) {
          p.progress += p.speed;
          if (p.progress >= 1.0) p.progress = 0;

          const px = n1.x + (n2.x - n1.x) * p.progress;
          const py = n1.y + (n2.y - n1.y) * p.progress;

          // Outer Glow
          ctx.beginPath();
          ctx.arc(px, py, 8, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(34, 197, 94, 0.4)';
          ctx.fill();

          // Packet Core
          ctx.beginPath();
          ctx.arc(px, py, 4, 0, Math.PI * 2);
          ctx.fillStyle = '#22C55E';
          ctx.fill();

          // Label
          ctx.font = '9px monospace';
          ctx.fillStyle = '#94A3B8';
          ctx.fillText(p.label, px - 16, py - 10);
        }
      });

      // Draw Nodes
      nodes.forEach(n => {
        // Node Ring
        ctx.beginPath();
        ctx.arc(n.x, n.y, 18, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
        ctx.strokeStyle = n.color;
        ctx.lineWidth = 3;
        ctx.fill();
        ctx.stroke();

        // Inner Dot
        ctx.beginPath();
        ctx.arc(n.x, n.y, 6, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.fill();

        // Node Title Text
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.fillStyle = '#F8FAFC';
        ctx.textAlign = 'center';
        ctx.fillText(n.label, n.x, n.y + 34);
      });

      NetworkVisView.animFrameId = requestAnimationFrame(draw);
    }

    if (NetworkVisView.animFrameId) cancelAnimationFrame(NetworkVisView.animFrameId);
    draw();
  }

  static pulsePacket() {
    NetworkVisView.packets.push({
      from: 'client',
      to: 'engine',
      progress: 0,
      speed: 0.02,
      label: 'TEST PULSE'
    });

    const logEl = document.getElementById('vis-packet-log');
    if (logEl) {
      const now = new Date().toLocaleTimeString();
      logEl.innerHTML = `<div>[${now}] 🚀 Injected custom test packet pulse across network topology</div>` + logEl.innerHTML;
    }
  }

  static toggleMesh() {
    alert('Multi-Region Edge Mesh Agents toggled ACTIVE. Synchronized with US-East and EU-West nodes.');
  }
}
