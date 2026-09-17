class MeshView {
  static async render(containerEl) {
    const agents = await ApiClient.fetchAgentMesh();
    const rows = agents.map(a => `
      <tr style="background: var(--bg-surface);">
        <td><strong>${a.name}</strong></td>
        <td><code>${a.region}</code></td>
        <td><code>${a.endpoint}</code></td>
        <td>${a.latency_ms} ms</td>
        <td><span class="badge short">${a.status}</span></td>
      </tr>
    `).join('');

    containerEl.innerHTML = `
      <div style="font-weight: 700; font-size: 16px; margin-bottom: 12px; color: var(--primary-blue);">🌐 Distributed Multi-Agent Edge Mesh Topology</div>
      <p style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 16px;">
        Deploy and orchestrate remote QUICLAB Edge Agents across global regions (US-East, EU-Central, AP-South) to execute multi-region latency & HTTP/3 load benchmarks simultaneously.
      </p>

      <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 20px;">
        <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 12px;">
          <input type="text" id="mesh-target" value="cloudflare-quic.com" style="flex: 1;" placeholder="Enter target domain or IP...">
          <button class="btn-run" onclick="MeshView.runBenchmark()">▶ Launch Multi-Region Mesh Benchmark</button>
        </div>
      </div>

      <div style="font-weight: 700; margin-bottom: 8px; font-size: 13px;">Registered Edge Mesh Nodes (${agents.length})</div>
      <table class="inspector-table" style="margin-bottom: 20px;">
        <thead>
          <tr>
            <th>Agent Name</th>
            <th>Region Code</th>
            <th>Endpoint Address</th>
            <th>Node Ping</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>

      <div id="mesh-benchmark-results" style="display: none;"></div>
    `;
  }

  static async runBenchmark() {
    const target = document.getElementById('mesh-target').value || 'cloudflare-quic.com';
    const resArea = document.getElementById('mesh-benchmark-results');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⚡ Dispatching simultaneous test requests across global edge mesh nodes to ${target}...</div>`;

    const res = await ApiClient.runMeshBenchmark(target);
    const rows = res.mesh_results.map(r => `
      <tr style="background: var(--bg-surface);">
        <td><strong>${r.agent_name}</strong></td>
        <td><code>${r.region}</code></td>
        <td><strong>${r.rtt_ms} ms</strong></td>
        <td>${r.http3_handshake_ms} ms</td>
        <td>${r.loss_pct}%</td>
        <td><span class="badge short">${r.status}</span></td>
      </tr>
    `).join('');

    resArea.innerHTML = `
      <div style="background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
        <strong>Multi-Region Benchmark Complete:</strong> Fastest Edge Region ➔ <strong>${res.fastest_region}</strong> (${res.agents_tested_count} Nodes Tested)
      </div>
      <table class="inspector-table">
        <thead>
          <tr>
            <th>Agent Node</th>
            <th>Region</th>
            <th>Network RTT</th>
            <th>HTTP/3 Handshake TTFB</th>
            <th>Packet Loss %</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }
}
