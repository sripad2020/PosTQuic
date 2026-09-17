class QUICInspectorView {
  static render(packets = [], containerEl) {
    if (!packets || packets.length === 0) {
      containerEl.innerHTML = `
        <div style="padding: 20px; color: var(--text-muted);">
          No QUIC packets captured yet. Run a QUIC or HTTP/3 request to inspect frames.
        </div>
      `;
      return;
    }

    let rows = packets.map(p => `
      <tr>
        <td>#${p.packet_num}</td>
        <td>${p.timestamp}</td>
        <td><strong style="color: ${p.direction === 'OUT' ? '#2563EB' : '#16A34A'}">${p.direction}</strong></td>
        <td><span class="badge ${p.packet_type.toLowerCase()}">${p.packet_type}</span></td>
        <td><code>${p.connection_id}</code></td>
        <td>${p.payload_size} bytes</td>
        <td>${p.encryption_level}</td>
        <td>
          <button class="btn-secondary" style="font-size: 10px; padding: 2px 6px;" onclick="QUICInspectorView.showFrameDetail('${p.id}')">Inspect Frames (${p.frames.length})</button>
        </td>
      </tr>
    `).join('');

    containerEl.innerHTML = `
      <div style="margin-bottom: 12px; font-weight: 700; font-size: 14px;">QUIC Packet Flight Inspector (${packets.length} Packets)</div>
      <table class="inspector-table">
        <thead>
          <tr>
            <th>Pkt #</th>
            <th>Timestamp</th>
            <th>Direction</th>
            <th>Type</th>
            <th>Connection ID</th>
            <th>Payload</th>
            <th>Encryption</th>
            <th>Frames Breakdown</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <div id="quic-frame-modal-area"></div>
    `;
    
    window._last_captured_packets = packets;
  }

  static showFrameDetail(packetId) {
    const pkts = window._last_captured_packets || [];
    const pkt = pkts.find(x => x.id === packetId);
    if (!pkt) return;

    const frameRows = pkt.frames.map(f => `
      <tr style="background: var(--bg-surface);">
        <td><strong style="color: var(--primary-blue);">${f.type}</strong></td>
        <td><code>${JSON.stringify(f)}</code></td>
      </tr>
    `).join('');

    const modalHtml = `
      <div class="modal-overlay" id="quic-modal-overlay">
        <div class="modal-card">
          <div class="modal-header">
            <div class="modal-title">Frame breakdown for Packet #${pkt.packet_num} (${pkt.packet_type})</div>
            <button class="btn-secondary" onclick="document.getElementById('quic-modal-overlay').remove()">✕</button>
          </div>
          <div class="modal-body">
            <table class="inspector-table">
              <thead>
                <tr>
                  <th>Frame Type</th>
                  <th>Decoded Payload Parameters</th>
                </tr>
              </thead>
              <tbody>${frameRows}</tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    document.getElementById('quic-frame-modal-area').innerHTML = modalHtml;
  }
}
