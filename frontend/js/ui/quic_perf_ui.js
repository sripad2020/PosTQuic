class QUICPerfStudioView {
  static render(containerEl) {
    containerEl.innerHTML = `
      <div style="font-weight: 700; font-size: 16px; margin-bottom: 12px; color: #2563EB;">⚡ QUIC High-Efficiency & Performance Optimization Studio</div>
      <p style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 16px;">
        Optimize QUIC transport throughput: UDP GSO Kernel Offload, BDP (Bandwidth-Delay Product) Window Auto-Tuning, Connection Handle Pooling, and Zero-Copy Packet Buffering.
      </p>

      <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 20px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px;">
          <div>
            <label style="font-weight: 600; display: block; margin-bottom: 4px;">Path RTT (ms):</label>
            <input type="number" id="perf-rtt" value="25" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block; margin-bottom: 4px;">Path Bandwidth (Mbps):</label>
            <input type="number" id="perf-bw" value="100" style="width: 100%;">
          </div>
        </div>

        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button class="btn-primary" style="background: #2563EB; border-color: #2563EB;" onclick="QUICPerfStudioView.autotuneBdp()">🎯 Auto-Tune Flow-Control BDP Windows</button>
          <button class="btn-secondary" onclick="QUICPerfStudioView.runGsoBench()">⚡ Benchmark UDP GSO Offload</button>
          <button class="btn-secondary" onclick="QUICPerfStudioView.checkPool()">🔄 Inspect Active Connection Pool</button>
        </div>
      </div>

      <div id="perf-results-area" style="display: none;"></div>
    `;
  }

  static async autotuneBdp() {
    const rtt = parseFloat(document.getElementById('perf-rtt').value || '25');
    const bw = parseFloat(document.getElementById('perf-bw').value || '100');
    const resArea = document.getElementById('perf-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Auto-tuning BDP flow control windows for ${rtt}ms RTT @ ${bw} Mbps...</div>`;

    const res = await ApiClient.runQUICAutoTuneBdp(rtt, bw);
    resArea.innerHTML = `
      <div style="background: #EFF6FF; border: 1px solid #BFDBFE; color: #1E40AF; padding: 14px; border-radius: 6px; margin-bottom: 14px;">
        <strong>BDP Window Auto-Tuning Complete:</strong> ${res.performance_gain}<br>
        • Calculated BDP: <strong>${(res.calculated_bdp_bytes / 1024).toFixed(1)} KB</strong>
      </div>
      <div style="font-weight: 700; margin-bottom: 8px;">Auto-Tuned Transport Parameters</div>
      <pre style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); font-family: var(--font-mono); font-size: 11.5px;">${JSON.stringify(res.autotuned_parameters, null, 2)}</pre>
    `;
  }

  static async runGsoBench() {
    const resArea = document.getElementById('perf-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Benchmarking UDP GSO kernel single-syscall packet batching...</div>`;

    const res = await ApiClient.runQUICGSOBenchmark();
    resArea.innerHTML = `
      <div style="background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 14px; border-radius: 6px; margin-bottom: 14px;">
        <strong>UDP GSO Kernel Offload Active:</strong> ${res.throughput_boost}<br>
        • CPU System Call Reduction: <strong>${res.cpu_overhead_reduction_pct}%</strong>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
        <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-size: 11px; color: var(--text-muted);">Standard UDP Syscalls (1,000 Pkts)</div>
          <div style="font-size: 20px; font-weight: 700; color: var(--status-red);">${res.standard_syscalls_for_1000_packets} calls</div>
        </div>
        <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-size: 11px; color: var(--text-muted);">GSO Batched Syscalls (1,000 Pkts)</div>
          <div style="font-size: 20px; font-weight: 700; color: var(--status-green);">${res.gso_batched_syscalls_for_1000_packets} calls</div>
        </div>
      </div>
    `;
  }

  static async checkPool() {
    const resArea = document.getElementById('perf-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Inspecting active QUIC connection handles in pool...</div>`;

    const res = await ApiClient.fetchQUICPoolStatus();
    const rows = res.pooled_connections.map(c => `
      <tr style="background: var(--bg-surface);">
        <td><code>${c.cid}</code></td>
        <td><strong>${c.host}</strong></td>
        <td>${c.streams_active} active</td>
        <td><span class="badge short">${c.state}</span></td>
      </tr>
    `).join('');

    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 12px;">
        <strong>Connection Pool Active:</strong> Reused ${res.total_pooled_connections} handles | Handshake Latency Saved: <strong>${res.handshake_latency_saved_ms} ms</strong>
      </div>
      <table class="inspector-table">
        <thead><tr><th>Connection ID</th><th>Endpoint</th><th>Active Streams</th><th>State</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }
}
