class FuzzerView {
  static render(containerEl) {
    containerEl.innerHTML = `
      <div style="font-weight: 700; font-size: 16px; margin-bottom: 12px; color: var(--status-red);">☣️ QUIC & Protocol Security Fuzzing Engine</div>
      <p style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 16px;">
        Inject mutated packet headers, malformed CRYPTO frames, overflowed stream offsets, and out-of-order flights to test server state exhaustion and crash resilience.
      </p>

      <div style="background: var(--bg-surface); padding: 16px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 20px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; margin-bottom: 14px;">
          <div>
            <label style="font-weight: 600; display: block; margin-bottom: 4px;">Target Host:</label>
            <input type="text" id="fuzz-host" value="quic.tech" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Port:</label>
            <input type="number" id="fuzz-port" value="4433" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Protocol:</label>
            <select id="fuzz-proto" style="width: 100%;">
              <option value="QUIC">QUIC v1 (RFC 9000)</option>
              <option value="HTTP/3">HTTP/3</option>
              <option value="RAW UDP">Raw UDP Datagrams</option>
            </select>
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Mutation Iterations:</label>
            <input type="number" id="fuzz-iterations" value="10" style="width: 100%;">
          </div>
        </div>
        <button class="btn-primary" style="background: var(--status-red); border-color: var(--status-red);" onclick="FuzzerView.runCampaign()">▶ Launch Fuzzing Campaign</button>
      </div>

      <div id="fuzz-results-area" style="display: none;"></div>
    `;
  }

  static async runCampaign() {
    const host = document.getElementById('fuzz-host').value;
    const port = parseInt(document.getElementById('fuzz-port').value);
    const proto = document.getElementById('fuzz-proto').value;
    const iterations = parseInt(document.getElementById('fuzz-iterations').value);

    const resArea = document.getElementById('fuzz-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Executing ${iterations} fuzzed mutations against ${host}:${port}...</div>`;

    try {
      const res = await ApiClient.runFuzzCampaign(host, port, proto, iterations);

      const auditRows = res.mutation_audit_trail.map(a => `
        <tr style="background: ${a.anomaly ? '#FEE2E2' : 'var(--bg-surface)'};">
          <td><code>${a.test_id}</code></td>
          <td>${a.timestamp}</td>
          <td><strong style="color: var(--status-red);">${a.mutation_vector}</strong></td>
          <td><code>${a.target_response}</code></td>
          <td>${a.rtt_ms} ms</td>
          <td>${a.anomaly ? `<span style="color: var(--status-red); font-weight: 600;">${a.anomaly}</span>` : 'Normal Shutdown'}</td>
        </tr>
      `).join('');

      resArea.innerHTML = `
        <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 16px;">
          <div style="font-size: 15px; font-weight: 700; margin-bottom: 8px;">Fuzzing Campaign Summary</div>
          <div style="display: flex; gap: 20px; font-size: 13px;">
            <div>Target: <strong>${res.target}</strong></div>
            <div>Server Survival Rate: <strong style="color: var(--status-green);">${res.survival_rate_pct}%</strong></div>
            <div>Resets: <strong>${res.anomalies_summary.resets}</strong></div>
            <div>Timeouts: <strong>${res.anomalies_summary.timeouts}</strong></div>
          </div>
        </div>

        <div style="font-weight: 700; margin-bottom: 8px;">Mutation Audit Trail</div>
        <table class="inspector-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Time</th>
              <th>Mutation Vector</th>
              <th>Target Server Response</th>
              <th>RTT</th>
              <th>Anomaly Audit</th>
            </tr>
          </thead>
          <tbody>${auditRows}</tbody>
        </table>
      `;
    } catch (e) {
      resArea.innerHTML = `<div style="color: var(--status-red);">Fuzzing Error: ${e.message}</div>`;
    }
  }
}
