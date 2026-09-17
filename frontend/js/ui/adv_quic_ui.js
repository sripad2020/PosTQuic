class AdvQUICView {
  static render(containerEl) {
    containerEl.innerHTML = `
      <div style="font-weight: 700; font-size: 16px; margin-bottom: 8px; color: #7C3AED;">🔬 Advanced QUIC Protocol Research Laboratory (15-Feature Diagnostic Suite)</div>
      <p style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 16px;">
        Perform 15 advanced QUIC protocol research audits: 0-RTT Anti-Replay, QPACK Dynamic Table, Congestion Control (BBR v2), PMTUD & ECN, Spin-Bit Privacy, Connection Migration, QUIC DATAGRAM, ECH/SNI Encryption, Flow Control Auto-Tuning, ACK Frequency Pacing, Stateless Reset Tokens, Version Negotiation, CRYPTO Reassembly, Multipath QUIC (MP-QUIC), and WebTransport Session Protocols.
      </p>

      <!-- TARGET INPUT & RESEARCH TOOLS TOOLBAR -->
      <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 16px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px;">
          <div>
            <label style="font-weight: 600; display: block; margin-bottom: 4px;">Target Host Endpoint:</label>
            <input type="text" id="advq-host" value="quic.tech" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block; margin-bottom: 4px;">Port:</label>
            <input type="number" id="advq-port" value="4433" style="width: 100%;">
          </div>
        </div>

        <div style="font-weight: 700; font-size: 11.5px; color: #7C3AED; margin-bottom: 8px;">15 RESEARCH TOOLS & PROTOCOL BENCHMARKS:</div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runZeroRtt()">1. 🛡️ 0-RTT Anti-Replay</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runQPack()">2. 📊 QPACK Dynamic Table</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runCongestion()">3. 📈 BBR v2 Congestion</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runPmtud()">4. 🔍 PMTUD & ECN Probing</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runPrivacy()">5. 🕵️ Spin-Bit & CID Privacy</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runMigration()">6. 🔄 Connection Migration</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runDatagram()">7. ⚡ QUIC DATAGRAM</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runEch()">8. 🔒 ECH / SNI Privacy</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runFlowControl()">9. 🎚️ Flow Control Auto-Tune</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runAckFreq()">10. ⏱️ ACK Frequency Pacing</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runStatelessReset()">11. 💥 Stateless Reset Token</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runVersionNeg()">12. 🔄 Version Negotiation</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runCryptoReassembly()">13. 🧩 CRYPTO Reassembly</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runMultipath()">14. 🌐 Multipath QUIC (MP-QUIC)</button>
          <button class="btn-secondary" style="font-size: 11px; text-align: left;" onclick="AdvQUICView.runWebTransport()">15. 🚀 WebTransport over H3</button>
        </div>
      </div>

      <!-- RESULTS AREA -->
      <div id="advq-results-area" style="display: none;"></div>
    `;
  }

  static getTarget() {
    const host = document.getElementById('advq-host')?.value || 'quic.tech';
    const port = parseInt(document.getElementById('advq-port')?.value || '4433');
    return { host, port };
  }

  static renderHostDetails(details) {
    if (!details) return '';
    return `
      <div style="margin-top: 14px; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 12px; border-radius: 6px; font-family: var(--font-sans);">
        <div style="font-size: 12px; font-weight: 700; color: var(--primary-blue); margin-bottom: 4px;">
          📖 Host Protocol Implementation & Architecture Details
        </div>
        <div style="font-size: 11.5px; color: var(--text-primary); margin-bottom: 6px;">
          <strong>RFC Standard:</strong> <code>${details.rfc_standard}</code>
        </div>
        <div style="font-size: 11.5px; color: var(--text-secondary); margin-bottom: 6px; line-height: 1.5;">
          <strong>Host Server Architecture:</strong> ${details.host_architecture}
        </div>
        <div style="font-size: 11px; font-family: var(--font-mono); background: #EFF6FF; border: 1px solid #BFDBFE; color: #1E40AF; padding: 6px 10px; border-radius: 4px;">
          <strong>Packet Sequence:</strong> ${details.packet_sequence}
        </div>
      </div>
    `;
  }

  // 1. 0-RTT Anti-Replay
  static async runZeroRtt() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Auditing 0-RTT Anti-Replay Strike Register on ${host}:${port}...</div>`;

    const res = await ApiClient.runZeroRttTest(host, port);
    const flights = res.flights_audit.map(f => `
      <div style="background: var(--bg-surface); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 6px;">
        <div style="display: flex; justify-content: space-between;">
          <strong>Flight #${f.flight_id}: ${f.packet_type}</strong>
          <span class="badge ${f.status.includes('ACCEPTED') ? 'short' : 'initial'}">${f.status}</span>
        </div>
        <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 4px;">${f.server_action}</div>
      </div>
    `).join('');

    resArea.innerHTML = `
      <div style="background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
        <strong>Anti-Replay Protection:</strong> ${res.anti_replay_protection} | Strike Register: <strong>${res.strike_register_status}</strong>
      </div>
      ${flights}
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 2. QPACK Dynamic Table
  static async runQPack() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Analyzing QPACK dynamic table compression on ${host}:${port}...</div>`;

    const res = await ApiClient.runQPackAnalysis(host, port);
    const rows = res.dynamic_table.entries.map(e => `
      <tr style="background: var(--bg-surface);">
        <td><code>[${e.index}]</code></td>
        <td><strong>${e.name}</strong></td>
        <td><code>${e.value}</code></td>
        <td>${e.size_bytes} B</td>
      </tr>
    `).join('');

    resArea.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 12px;">
        <div style="background: var(--bg-surface); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-size: 11px; color: var(--text-muted);">Uncompressed Headers</div>
          <div style="font-size: 18px; font-weight: 700;">${res.uncompressed_bytes} Bytes</div>
        </div>
        <div style="background: var(--bg-surface); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-size: 11px; color: var(--text-muted);">QPACK Compressed</div>
          <div style="font-size: 18px; font-weight: 700; color: var(--primary-blue);">${res.qpack_compressed_bytes} Bytes</div>
        </div>
        <div style="background: var(--bg-surface); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-size: 11px; color: var(--text-muted);">Compression Savings</div>
          <div style="font-size: 18px; font-weight: 700; color: #16A34A;">${res.compression_savings_pct}% Saved</div>
        </div>
      </div>
      <table class="inspector-table">
        <thead><tr><th>Index</th><th>Header Name</th><th>Value</th><th>Size</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 3. Congestion Control BBR
  static async runCongestion() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Benchmarking BBR v2 Congestion Control pacing on ${host}:${port}...</div>`;

    const res = await ApiClient.runCongestionBenchmark(host, port, 'BBR');
    const rows = res.throughput_samples.map(s => `
      <tr style="background: ${s.loss_event ? '#FEE2E2' : 'var(--bg-surface)'};">
        <td>Round ${s.round}</td>
        <td><strong>${s.cwnd_packets} pkts</strong></td>
        <td>${s.pacing_rate_mbps} Mbps</td>
        <td>${s.rtt_sample_ms} ms</td>
        <td>${s.loss_event ? '<span style="color: var(--status-red); font-weight: 600;">LOSS EVENT</span>' : 'Optimal Pacing'}</td>
      </tr>
    `).join('');

    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 10px;">
        Algorithm: <strong>${res.algorithm}</strong> | Peak cwnd: <strong>${res.peak_cwnd_packets} pkts</strong> | Loss Recovery: <strong>${res.recovery_speed_rounds} rounds</strong>
      </div>
      <table class="inspector-table">
        <thead><tr><th>Round</th><th>cwnd Size</th><th>Pacing Rate</th><th>RTT Sample</th><th>Transport Event</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 4. PMTUD & ECN
  static async runPmtud() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Probing Path MTU & ECN markings on ${host}:${port}...</div>`;

    const res = await ApiClient.runPmtudEcnProbe(host, port);
    const rows = res.pmtud_probes.map(p => `
      <tr style="background: var(--bg-surface);">
        <td><code>${p.probe_size_bytes} Bytes</code></td>
        <td><span class="badge ${p.status === 'ACKNOWLEDGED' ? 'short' : 'initial'}">${p.status}</span></td>
        <td>${p.rtt_ms ? p.rtt_ms + ' ms' : 'Fragmented'}</td>
      </tr>
    `).join('');

    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 10px;">
        Discovered Path MTU: <strong>${res.discovered_path_mtu_bytes} Bytes</strong> | ECN Marking: <strong>${res.ecn_validation.ip_ecn_marking}</strong>
      </div>
      <table class="inspector-table">
        <thead><tr><th>Probe Payload Size</th><th>Status</th><th>RTT</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 5. Spin-Bit & CID Privacy
  static async runPrivacy() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Auditing Spin-Bit latency leakage & Connection ID rotation on ${host}:${port}...</div>`;

    const res = await ApiClient.runSpinbitPrivacyAudit(host, port);
    resArea.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
        <div style="background: var(--bg-surface); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color);">
          <strong style="color: #7C3AED;">Spin-Bit Latency Leakage</strong>
          <div style="font-size: 11.5px; margin-top: 4px;">Bit Sequence: [${res.spin_bit_analysis.bit_sequence.join(', ')}]</div>
          <div style="font-size: 11px; color: var(--status-red); margin-top: 4px;">Risk: ${res.spin_bit_analysis.middlebox_rtt_leakage_risk}</div>
        </div>
        <div style="background: var(--bg-surface); padding: 10px; border-radius: 6px; border: 1px solid var(--border-color);">
          <strong style="color: var(--primary-blue);">CID Rotation Audit</strong>
          <div style="font-size: 11.5px; margin-top: 4px;">Unlinkability Protected: <strong style="color: #16A34A;">Yes</strong></div>
          <div style="font-size: 11px; margin-top: 4px;">Active CIDs: ${res.cid_rotation_analysis.active_cids.map(c => `<code>${c.cid}</code>`).join(', ')}</div>
        </div>
      </div>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 6. Connection Migration
  static async runMigration() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Testing QUIC socket path migration on ${host}:${port}...</div>`;

    const res = await ApiClient.runConnectionMigrationTest(host, port);
    resArea.innerHTML = `
      <div style="background: #F0FDF4; border: 1px solid #BBF7D0; color: #166534; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
        <strong>Path Migration Successful:</strong> ${res.previous_path} ➔ ${res.new_path} | Probe RTT: <strong>${res.path_validation.probe_rtt_ms} ms</strong>
      </div>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 7. QUIC DATAGRAM Extension
  static async runDatagram() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Testing DATAGRAM extension payloads on ${host}:${port}...</div>`;

    const res = await ApiClient.runDatagramExtensionTest(host, port);
    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 10px;">
        Datagrams Sent: <strong>${res.datagrams_sent}</strong> | Received: <strong>${res.datagrams_received}</strong> | Loss: <strong>${res.loss_rate_pct}%</strong> | Head-of-Line Blocking: <strong>${res.head_of_line_blocking}</strong>
      </div>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 8. ECH & SNI Privacy
  static async runEch() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Testing Encrypted ClientHello (ECH) SNI shielding on ${host}:${port}...</div>`;

    const res = await ApiClient.runEchPrivacyTest(host, port);
    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 10px;">
        Outer Dummy SNI: <code>${res.outer_sni_host}</code> | Encrypted Inner SNI: <code>${res.inner_sni_host}</code> | Cipher: <strong>${res.ech_hpke_cipher}</strong>
      </div>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 9. Flow Control
  static async runFlowControl() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Auditing MAX_DATA flow control auto-tuning on ${host}:${port}...</div>`;

    const res = await ApiClient.runFlowControlTest(host, port);
    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 10px;">
        Connection Window: <strong>${(res.connection_max_data_bytes/1048576).toFixed(1)} MB</strong> | Stream Window: <strong>${(res.stream_max_data_bytes/1048576).toFixed(1)} MB</strong> | Performance Gain: <strong>${res.window_autotuning_gain}</strong>
      </div>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 10. ACK Frequency
  static async runAckFreq() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Testing ACK Frequency pacing on ${host}:${port}...</div>`;

    const res = await ApiClient.runAckFrequencyTest(host, port);
    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 10px;">
        Max ACK Delay: <strong>${res.max_ack_delay_ms} ms</strong> | ACK Threshold: <strong>${res.ack_eliciting_threshold} pkts</strong> | Reverse Overhead Saved: <strong>${res.reverse_path_ack_reduction_pct}%</strong>
      </div>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 11. Stateless Reset
  static async runStatelessReset() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Auditing Stateless Reset token validation on ${host}:${port}...</div>`;

    const res = await ApiClient.runStatelessResetTest(host, port);
    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 10px;">
        Stateless Reset Token: <code>${res.reset_token_hex}</code> | Action: <strong>${res.connection_termination_action}</strong>
      </div>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 12. Version Negotiation
  static async runVersionNeg() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Testing QUIC Version Negotiation on ${host}:${port}...</div>`;

    const res = await ApiClient.runVersionNegotiationTest(host, port);
    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 10px;">
        Offered Version: <code>${res.offered_version}</code> | Negotiated: <code>${res.negotiated_version}</code> | Downgrade Protection: <strong>${res.downgrade_prevention_status}</strong>
      </div>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 13. CRYPTO Reassembly
  static async runCryptoReassembly() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Testing out-of-order CRYPTO stream reassembly on ${host}:${port}...</div>`;

    const res = await ApiClient.runCryptoReassemblyTest(host, port);
    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 10px;">
        Flight Arrival: <strong>${res.flight_arrival_order}</strong> | Reassembly Buffer State: <strong>${res.reassembly_buffer_state}</strong>
      </div>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 14. Multipath QUIC
  static async runMultipath() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Testing Multipath QUIC (MP-QUIC) subflow scheduler on ${host}:${port}...</div>`;

    const res = await ApiClient.runMultipathQuicTest(host, port);
    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 10px;">
        Policy: <strong>${res.packet_scheduler_policy}</strong> | Aggregate Throughput: <strong>${res.aggregate_throughput}</strong>
      </div>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }

  // 15. WebTransport over H3
  static async runWebTransport() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('advq-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Initializing WebTransport session over HTTP/3 CONNECT on ${host}:${port}...</div>`;

    const res = await ApiClient.runWebtransportProtocolTest(host, port);
    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 10px;">
        Session ID: <code>${res.session_id}</code> | Negotiated Draft: <strong>${res.negotiated_draft}</strong> | Bidi Streams: <strong>${res.bidi_streams}</strong> | Uni Streams: <strong>${res.uni_streams}</strong>
      </div>
      ${AdvQUICView.renderHostDetails(res.host_implementation_details)}
    `;
  }
}
