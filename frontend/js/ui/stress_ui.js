class StressView {
  static render(containerEl) {
    containerEl.innerHTML = `
      <div style="font-weight: 700; font-size: 16px; margin-bottom: 12px; color: var(--primary-blue);">🚀 High-Throughput Load & Stress Generator</div>
      <p style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 16px;">
        Spawn concurrent async load workers to benchmark HTTP/3, QUIC, and UDP datagram performance, computing p50/p90/p95/p99 latency percentiles and RPS throughput.
      </p>

      <div style="background: var(--bg-surface); padding: 16px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 20px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 14px;">
          <div>
            <label style="font-weight: 600; display: block; margin-bottom: 4px;">Target URL / Endpoint:</label>
            <input type="text" id="stress-url" value="https://cloudflare-quic.com/" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Concurrent Workers:</label>
            <input type="number" id="stress-concurrency" value="50" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Total Requests:</label>
            <input type="number" id="stress-total" value="300" style="width: 100%;">
          </div>
        </div>
        <button class="btn-run" onclick="StressView.runStressTest()">▶ Launch Stress Generator</button>
      </div>

      <div id="stress-results-area" style="display: none;"></div>
    `;
  }

  static async runStressTest() {
    const url = document.getElementById('stress-url').value;
    const concurrency = parseInt(document.getElementById('stress-concurrency').value);
    const total_requests = parseInt(document.getElementById('stress-total').value);

    const resArea = document.getElementById('stress-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⚡ Spawning ${concurrency} async workers to dispatch ${total_requests} requests...</div>`;

    try {
      const res = await ApiClient.runStressTest(url, concurrency, total_requests);

      const p = res.percentiles_ms;

      resArea.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
          
          <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color);">
            <div style="font-weight: 700; font-size: 14px; margin-bottom: 10px; color: var(--status-green);">Throughput Metrics</div>
            <div style="font-size: 24px; font-weight: 700; color: var(--primary-blue);">${res.requests_per_second} RPS</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
              Total Duration: ${res.total_duration_sec} sec | Total Executed: ${res.total_requests}
            </div>
            <div style="margin-top: 10px; font-size: 12px;">
              Success: <strong style="color: var(--status-green);">${res.successful_requests}</strong> | 
              Failed: <strong style="color: var(--status-red);">${res.failed_requests}</strong>
            </div>
          </div>

          <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color);">
            <div style="font-weight: 700; font-size: 14px; margin-bottom: 10px; color: var(--primary-blue);">Latency Percentiles</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-family: var(--font-mono); font-size: 12px;">
              <div>p50 (Median): <strong>${p.p50} ms</strong></div>
              <div>p90: <strong>${p.p90} ms</strong></div>
              <div>p95: <strong>${p.p95} ms</strong></div>
              <div>p99 (Tail): <strong>${p.p99} ms</strong></div>
              <div>Min: ${p.min} ms</div>
              <div>Max: ${p.max} ms</div>
            </div>
          </div>

        </div>
      `;
    } catch (e) {
      resArea.innerHTML = `<div style="color: var(--status-red);">Stress Test Error: ${e.message}</div>`;
    }
  }
}
