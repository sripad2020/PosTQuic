class CorrelationView {
  static render(correlationData = null, containerEl) {
    if (!correlationData) {
      containerEl.innerHTML = `<div style="padding: 20px; color: var(--text-muted);">Execute an HTTP/3 or MoQ request to view cross-layer protocol stack correlation.</div>`;
      return;
    }

    const appLayer = correlationData.application_layer || {};
    const streamLayer = correlationData.quic_stream_layer || {};
    const pktLayer = correlationData.quic_packet_layer || {};
    const transportLayer = correlationData.transport_layer || {};

    containerEl.innerHTML = `
      <div style="font-weight: 700; font-size: 15px; margin-bottom: 14px;">Cross-Layer Navigation Correlation Inspector</div>
      <div style="display: flex; flex-direction: column; gap: 12px;">
        
        <!-- LAYER 1: Application -->
        <div style="border: 2px solid #2563EB; background: #EFF6FF; padding: 12px; border-radius: 6px;">
          <div style="font-weight: 700; color: #1D4ED8;">Application Layer: ${appLayer.protocol || 'HTTP/3'} (${appLayer.method || 'GET'})</div>
          <div style="font-family: var(--font-mono); font-size: 11.5px; margin-top: 4px;">${appLayer.url || ''}</div>
        </div>

        <div style="text-align: center; color: var(--text-muted);">↓ Encapsulated into Stream</div>

        <!-- LAYER 2: QUIC Stream -->
        <div style="border: 2px solid #7C3AED; background: #F5F3FF; padding: 12px; border-radius: 6px;">
          <div style="font-weight: 700; color: #6D28D9;">QUIC Stream Layer: Stream ID ${streamLayer.stream_id ?? 0} (${streamLayer.stream_type || 'Control'})</div>
          <div style="font-family: var(--font-mono); font-size: 11.5px; margin-top: 4px;">State: ${streamLayer.state || 'CLOSED'} | Bytes Tx: ${streamLayer.bytes_sent || 0} | Bytes Rx: ${streamLayer.bytes_received || 0}</div>
        </div>

        <div style="text-align: center; color: var(--text-muted);">↓ Framed into QUIC Packet</div>

        <!-- LAYER 3: QUIC Packet -->
        <div style="border: 2px solid #059669; background: #ECFDF5; padding: 12px; border-radius: 6px;">
          <div style="font-weight: 700; color: #047857;">QUIC Packet Layer: Packet #${pktLayer.packet_number || 4} (${pktLayer.packet_type || '1-RTT'})</div>
          <div style="font-family: var(--font-mono); font-size: 11.5px; margin-top: 4px;">Connection ID: ${pktLayer.connection_id || ''} | Frames: ${(pktLayer.frames || []).join(', ')}</div>
        </div>

        <div style="text-align: center; color: var(--text-muted);">↓ Transported over UDP Datagram</div>

        <!-- LAYER 4: Transport -->
        <div style="border: 2px solid #D97706; background: #FFFBEB; padding: 12px; border-radius: 6px;">
          <div style="font-weight: 700; color: #B45309;">Transport Layer: ${transportLayer.protocol || 'UDP'}</div>
          <div style="font-family: var(--font-mono); font-size: 11.5px; margin-top: 4px;">Endpoint: ${transportLayer.src_endpoint || '127.0.0.1'} ➔ ${transportLayer.dst_endpoint || 'Target'} | Size: ${transportLayer.payload_size_bytes || 0} bytes</div>
        </div>

      </div>
    `;
  }
}
