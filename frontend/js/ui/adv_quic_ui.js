// Advanced QUIC Protocol Research Laboratory.
// Every test runs real QUIC connections on the backend (app/protocols/quic_lab.py)
// and returns: status, verdict, summary [[label, value]], table {columns, rows}.
const ADVQ_TESTS = [
  { id: 'zerortt',   label: '1. 🛡️ 0-RTT & Ticket Reuse',        busy: 'Running full handshake + two 0-RTT resumptions', call: (h, p) => ApiClient.runZeroRttTest(h, p) },
  { id: 'qpack',     label: '2. 📊 QPACK Compression',            busy: 'Sending two real HTTP/3 requests',               call: (h, p) => ApiClient.runQPackAnalysis(h, p) },
  { id: 'cc',        label: '3. 📈 Congestion Control (CUBIC)',   busy: 'Uploading ~4 MB and sampling the congestion window', call: (h, p) => ApiClient.runCongestionBenchmark(h, p, 'cubic') },
  { id: 'pmtud',     label: '4. 🔍 Path MTU (ECN n/a)',           busy: 'Probing datagram sizes with Don\'t-Fragment set', call: (h, p) => ApiClient.runPmtudEcnProbe(h, p) },
  { id: 'privacy',   label: '5. 🕵️ Spin Bit & CID Rotation',      busy: 'Observing the spin bit and rotating connection IDs', call: (h, p) => ApiClient.runSpinbitPrivacyAudit(h, p) },
  { id: 'migration', label: '6. 🔄 Connection Migration',         busy: 'Moving the live connection to a new UDP socket', call: (h, p) => ApiClient.runConnectionMigrationTest(h, p) },
  { id: 'datagram',  label: '7. ⚡ QUIC DATAGRAM',                busy: 'Negotiating DATAGRAM and sending 20 frames',     call: (h, p) => ApiClient.runDatagramExtensionTest(h, p) },
  { id: 'ech',       label: '8. 🔒 ECH (DNS HTTPS record)',       busy: 'Looking up the DNS HTTPS record',                call: (h, p) => ApiClient.runEchPrivacyTest(h, p) },
  { id: 'flow',      label: '9. 🎚️ Flow Control Limits',          busy: 'Reading flow-control limits and downloading a page', call: (h, p) => ApiClient.runFlowControlTest(h, p) },
  { id: 'ack',       label: '10. ⏱️ ACK Behaviour',               busy: 'Uploading for ~2 s and counting ACKs',           call: (h, p) => ApiClient.runAckFrequencyTest(h, p) },
  { id: 'reset',     label: '11. 💥 Stateless Reset',             busy: 'Closing a connection and probing its dead CID',  call: (h, p) => ApiClient.runStatelessResetTest(h, p) },
  { id: 'vn',        label: '12. 🔄 Version Negotiation',         busy: 'Offering a reserved QUIC version',               call: (h, p) => ApiClient.runVersionNegotiationTest(h, p) },
  { id: 'crypto',    label: '13. 🧩 CRYPTO Reassembly',           busy: 'Sending the ClientHello packets in reverse order', call: (h, p) => ApiClient.runCryptoReassemblyTest(h, p) },
  { id: 'multipath', label: '14. 🌐 Multipath (not supported)',   busy: 'Listing local interfaces',                       call: (h, p) => ApiClient.runMultipathQuicTest(h, p) },
  { id: 'wt',        label: '15. 🚀 WebTransport over H3',        busy: 'Reading SETTINGS and sending Extended CONNECT',  call: (h, p) => ApiClient.runWebtransportProtocolTest(h, p) },
];

class AdvQUICView {
  static render(containerEl) {
    const buttons = ADVQ_TESTS.map(t =>
      `<button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.run('${t.id}')">${t.label}</button>`
    ).join('');
    containerEl.innerHTML = `
      <div style="font-weight: 700; font-size: 16px; margin-bottom: 8px; color: #7C3AED;">🔬 Advanced QUIC Protocol Research Laboratory</div>
      <p style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 16px;">
        15 experiments that open real QUIC connections (aioquic) against the target and report what the server actually did.
        Features the QUIC engine cannot exercise (multipath, ECN, the ACK-frequency extension, sending ECH) are reported as not supported rather than simulated.
      </p>

      <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 16px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px;">
          <div>
            <label style="font-weight: 600; display: block; margin-bottom: 4px;">Target Host Endpoint:</label>
            <input type="text" id="advq-host" value="cloudflare-quic.com" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block; margin-bottom: 4px;">Port:</label>
            <input type="number" id="advq-port" value="443" style="width: 100%;">
          </div>
        </div>
        <div style="font-weight: 700; font-size: 11.5px; color: #7C3AED; margin-bottom: 8px;">RESEARCH TOOLS:</div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">${buttons}</div>
      </div>

      <div id="advq-results-area" style="display: none;"></div>
    `;
  }

  static getTarget() {
    const host = (document.getElementById('advq-host')?.value || 'cloudflare-quic.com').trim();
    const port = parseInt(document.getElementById('advq-port')?.value || '443', 10);
    return { host, port };
  }

  static esc(v) {
    return String(v ?? '—').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  static async run(testId) {
    const test = ADVQ_TESTS.find(t => t.id === testId);
    if (!test) return;
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ ${this.esc(test.busy)} on ${this.esc(host)}:${port}...</div>`;
    let res;
    try {
      res = await test.call(host, port);
    } catch (err) {
      res = { status: 'TEST_FAILED', verdict: `UI error: ${err.message}`, summary: [], table: null };
    }
    resArea.innerHTML = this.renderResult(test.label, res);
  }

  static tone(status) {
    if (/FAILED|UNAVAILABLE/.test(status)) return { bg: '#FEF2F2', border: '#FECACA', fg: '#991B1B' };
    if (/NOT_SUPPORTED|NOT_PUBLISHED|NO_|DISABLED|NOT_OBSERVED/.test(status)) return { bg: '#FFFBEB', border: '#FDE68A', fg: '#92400E' };
    return { bg: '#ECFDF5', border: '#A7F3D0', fg: '#065F46' };
  }

  static renderResult(label, res) {
    const status = res.status || 'UNKNOWN';
    const t = this.tone(status);
    const summary = (res.summary || []).map(([k, v]) => `
      <div style="background: var(--bg-surface); padding: 8px 10px; border-radius: 6px; border: 1px solid var(--border-color);">
        <div style="font-size: 11px; color: var(--text-muted);">${this.esc(k)}</div>
        <div style="font-size: 13px; font-weight: 600; word-break: break-all;">${this.esc(v)}</div>
      </div>`).join('');
    const table = res.table && res.table.rows && res.table.rows.length ? `
      <div style="overflow-x: auto; margin-top: 12px;">
        <table class="inspector-table">
          <thead><tr>${res.table.columns.map(c => `<th>${this.esc(c)}</th>`).join('')}</tr></thead>
          <tbody>${res.table.rows.map(r => `<tr>${r.map(c => `<td>${this.esc(c)}</td>`).join('')}</tr>`).join('')}</tbody>
        </table>
      </div>` : '';
    return `
      <div style="font-weight: 700; margin-bottom: 8px;">${this.esc(label)} — <code>${this.esc(res.target)}</code></div>
      <div style="background: ${t.bg}; border: 1px solid ${t.border}; color: ${t.fg}; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
        <div style="font-size: 11px; font-weight: 700; letter-spacing: .03em;">${this.esc(status)}</div>
        <div style="margin-top: 4px;">${this.esc(res.verdict || res.error || '')}</div>
      </div>
      ${summary ? `<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px;">${summary}</div>` : ''}
      ${table}
      ${this.renderHostDetails(res.host_implementation_details)}
    `;
  }

  static renderHostDetails(details) {
    if (!details) return '';
    return `
      <div style="margin-top: 14px; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px; border-radius: 6px; font-family: var(--font-sans);">
        <div style="font-size: 12px; font-weight: 700; color: var(--primary-blue); margin-bottom: 4px;">📖 How this test works</div>
        <div style="font-size: 11.5px; color: var(--text-primary); margin-bottom: 6px;">
          <strong>Standard:</strong> <code>${this.esc(details.rfc_standard)}</code>
        </div>
        <div style="font-size: 11.5px; color: var(--text-secondary); margin-bottom: 6px; line-height: 1.5;">${this.esc(details.host_architecture)}</div>
        ${details.packet_sequence ? `<div style="font-size: 11px; font-family: var(--font-mono); background: #EFF6FF; border: 1px solid #BFDBFE; color: #1E40AF; padding: 6px 10px; border-radius: 4px;">
          <strong>Sequence:</strong> ${this.esc(details.packet_sequence)}
        </div>` : ''}
      </div>
    `;
  }

  // Back-compat: anything still calling the old per-test methods.
  static runZeroRtt() { return this.run('zerortt'); }
  static runQPack() { return this.run('qpack'); }
  static runCongestion() { return this.run('cc'); }
  static runPmtud() { return this.run('pmtud'); }
  static runPrivacy() { return this.run('privacy'); }
  static runMigration() { return this.run('migration'); }
  static runDatagram() { return this.run('datagram'); }
  static runEch() { return this.run('ech'); }
  static runFlowControl() { return this.run('flow'); }
  static runAckFreq() { return this.run('ack'); }
  static runStatelessReset() { return this.run('reset'); }
  static runVersionNeg() { return this.run('vn'); }
  static runCryptoReassembly() { return this.run('crypto'); }
  static runMultipath() { return this.run('multipath'); }
  static runWebTransport() { return this.run('wt'); }
}
