class QUICInjectorStudioView {
  static render(containerEl) {
    containerEl.innerHTML = `
      <div style="font-weight: 700; font-size: 16px; margin-bottom: 8px; color: #D97706;">💉 Advanced QUIC Custom Frame & Transport Parameter Injector Studio</div>
      <p style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 16px;">
        Construct, customize, and inject raw QUIC frames, transport parameters, bit-flip fault mutations, and version negotiation flights directly into target QUIC connections.
      </p>

      <!-- TARGET & INJECTION STUDIO GRID -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px;">
        
        <!-- SECTION 1: CUSTOM FRAME INJECTOR BUILDER -->
        <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-weight: 700; font-size: 13px; color: #D97706; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <span>📦 Custom QUIC Frame Injector</span>
            <span class="badge short" style="background: #FEF3C7; color: #92400E; border-color: #FDE68A;">DYNAMIC BUILDER</span>
          </div>

          <div style="margin-bottom: 10px;">
            <label style="font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px;">Select Frame Type:</label>
            <select id="inj-frame-type" style="width: 100%; font-size: 12px;" onchange="QUICInjectorStudioView.updateFormFields()">
              <option value="RESET_STREAM">RESET_STREAM (0x04 - Abort Stream)</option>
              <option value="STOP_SENDING">STOP_SENDING (0x05 - Request Stop)</option>
              <option value="MAX_STREAM_DATA">MAX_STREAM_DATA (0x11 - Window Expansion)</option>
              <option value="DATAGRAM">DATAGRAM (0x30 - RFC 9221 Unreliable Payload)</option>
              <option value="PING">PING (0x01 - Keepalive Probe)</option>
              <option value="PATH_CHALLENGE">PATH_CHALLENGE (0x1A - Migration Probe)</option>
              <option value="CONNECTION_CLOSE">CONNECTION_CLOSE (0x1C - Immediate Termination)</option>
            </select>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
            <div>
              <label style="font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px;">Stream ID:</label>
              <input type="number" id="inj-stream-id" value="4" style="width: 100%; font-size: 12px;">
            </div>
            <div>
              <label style="font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px;">Error Code (Dec/Hex):</label>
              <input type="number" id="inj-error-code" value="10" style="width: 100%; font-size: 12px;" placeholder="e.g. 10 (0x0A)">
            </div>
          </div>

          <div id="field-max-data" style="margin-bottom: 10px; display: none;">
            <label style="font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px;">Max Stream Data Limit (Bytes):</label>
            <input type="number" id="inj-max-data-limit" value="2097152" style="width: 100%; font-size: 12px;">
          </div>

          <div id="field-payload-text" style="margin-bottom: 12px;">
            <label style="font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px;">Custom Frame Payload (Text / Hex):</label>
            <input type="text" id="inj-payload-text" value="INJECTED_RAW_FRAME_PAYLOAD_0x1F" style="width: 100%; font-size: 12px; font-family: var(--font-mono);">
          </div>

          <button class="btn-run" style="width: 100%; background: #D97706; border-color: #D97706;" onclick="QUICInjectorStudioView.injectCustomFrame()">
            ▶ Inject Custom Frame into Connection
          </button>
        </div>

        <!-- SECTION 2: TRANSPORT PARAMETERS & FAULT MUTATION INJECTOR -->
        <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-weight: 700; font-size: 13px; color: var(--primary-blue); margin-bottom: 10px;">
            ⚡ Custom Transport Parameters & Fault Vectors
          </div>

          <div style="margin-bottom: 10px;">
            <label style="font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px;">Target Host & Port:</label>
            <div style="display: flex; gap: 8px;">
              <input type="text" id="inj-host" value="quic.tech" style="flex: 2; font-size: 12px;">
              <input type="number" id="inj-port" value="4433" style="flex: 1; font-size: 12px;">
            </div>
          </div>

          <div style="margin-bottom: 10px;">
            <label style="font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px;">Custom Transport Params (JSON):</label>
            <textarea id="inj-params-json" rows="3" style="width: 100%; font-family: var(--font-mono); font-size: 11.5px;">{\n  "initial_max_data": 2097152,\n  "initial_max_stream_data_bidi_local": 524288,\n  "initial_max_streams_bidi": 150,\n  "max_idle_timeout_ms": 60000\n}</textarea>
          </div>

          <div style="margin-bottom: 12px;">
            <label style="font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px;">Fault Mutation Vector:</label>
            <select id="inj-fault-type" style="width: 100%; font-size: 12px;">
              <option value="BIT_FLIP_HEADER_TYPE">Header Form Bit-Flip Corruption</option>
              <option value="PACKET_NUMBER_GAP">Packet Number Non-Sequential Gap</option>
              <option value="CRYPTO_KEY_SHARE_CORRUPTION">ECDHE Key Share Bytes Corruption</option>
              <option value="TRUNCATED_CONNECTION_ID">Truncated Connection ID</option>
              <option value="MALFORMED_VARINT_ENCODING">Malformed VarInt Variable Length Encoding</option>
            </select>
          </div>

          <div style="display: flex; gap: 8px;">
            <button class="btn-secondary" style="flex: 1; font-size: 11px;" onclick="QUICInjectorStudioView.injectParams()">⚡ Inject Params</button>
            <button class="btn-secondary" style="flex: 1; font-size: 11px; color: var(--status-red);" onclick="QUICInjectorStudioView.injectFault()">👾 Inject Fault</button>
            <button class="btn-secondary" style="flex: 1; font-size: 11px;" onclick="QUICInjectorStudioView.injectVersion()">🔄 Version Neg</button>
          </div>
        </div>

      </div>

      <!-- INJECTION OUTPUT & PACKET FLIGHT DIAGRAM -->
      <div id="inj-results-area" style="display: none;"></div>
    `;

    QUICInjectorStudioView.updateFormFields();
  }

  static updateFormFields() {
    const frameType = document.getElementById('inj-frame-type')?.value;
    const maxDataField = document.getElementById('field-max-data');
    if (maxDataField) {
      maxDataField.style.display = (frameType === 'MAX_STREAM_DATA' || frameType === 'MAX_DATA') ? 'block' : 'none';
    }
  }

  static getTarget() {
    const host = document.getElementById('inj-host')?.value || 'quic.tech';
    const port = parseInt(document.getElementById('inj-port')?.value || '4433');
    return { host, port };
  }

  static async injectCustomFrame() {
    const { host, port } = this.getTarget();
    const frameType = document.getElementById('inj-frame-type')?.value || 'RESET_STREAM';
    const streamId = parseInt(document.getElementById('inj-stream-id')?.value || '4');
    const errorCode = parseInt(document.getElementById('inj-error-code')?.value || '10');
    const maxDataLimit = parseInt(document.getElementById('inj-max-data-limit')?.value || '2097152');
    const payloadText = document.getElementById('inj-payload-text')?.value || '';

    const resArea = document.getElementById('inj-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Injecting custom ${frameType} frame on Stream ${streamId} into ${host}:${port}...</div>`;

    const res = await ApiClient.runQUICInjectFrame(host, port, frameType, streamId, errorCode, maxDataLimit, payloadText);

    resArea.innerHTML = `
      <!-- INJECTION SUCCESS BANNER -->
      <div style="background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 14px; border-radius: 6px; margin-bottom: 14px;">
        <div style="font-size: 14px; font-weight: 700; margin-bottom: 4px;">
          ✅ Custom Frame Injection Executed: ${res.injected_frame_type}
        </div>
        <div style="font-size: 12px;">
          Target Endpoint: <strong>${res.target}</strong> | Stream ID: <strong>${res.stream_id}</strong> | Error Code: <strong>${res.error_code_hex}</strong><br>
          Reaction: ${res.server_reaction}
        </div>
      </div>

      <!-- PACKET FLIGHT STRUCTURE VISUALIZER -->
      <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color);">
        <div style="font-weight: 700; font-size: 13px; margin-bottom: 8px; color: var(--primary-blue);">
          🔍 Injected Packet Structure & Payload Bytes
        </div>
        <pre style="margin: 0; font-family: var(--font-mono); font-size: 11.5px; background: var(--bg-muted); padding: 12px; border-radius: 4px;">${JSON.stringify(res.packet_details || res, null, 2)}</pre>
      </div>
    `;
  }

  static async injectParams() {
    const { host, port } = this.getTarget();
    const resArea = document.getElementById('inj-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Injecting custom QUIC Transport Parameters into ClientHello flight for ${host}:${port}...</div>`;

    let customParams = {};
    try {
      customParams = JSON.parse(document.getElementById('inj-params-json')?.value || '{}');
    } catch (e) {
      customParams = { initial_max_data: 2097152, initial_max_streams_bidi: 150 };
    }

    const res = await ApiClient.runQUICInjectParams(host, port, customParams);
    resArea.innerHTML = `
      <div style="background: #FFFBEB; border: 1px solid #FDE68A; color: #92400E; padding: 14px; border-radius: 6px; margin-bottom: 12px;">
        <strong>Transport Parameter Injection Complete:</strong> ${res.server_reaction}
      </div>
      <pre style="background: var(--bg-surface); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color); font-family: var(--font-mono); font-size: 11.5px;">${JSON.stringify(res.injected_parameters, null, 2)}</pre>
    `;
  }

  static async injectFault() {
    const { host, port } = this.getTarget();
    const faultType = document.getElementById('inj-fault-type')?.value || 'BIT_FLIP_HEADER_TYPE';

    const resArea = document.getElementById('inj-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Injecting ${faultType} fault mutation test against ${host}:${port}...</div>`;

    const res = await ApiClient.runQUICInjectFault(host, port, faultType);
    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color);">
        <div style="font-weight: 700; font-size: 14px; color: var(--status-red); margin-bottom: 6px;">Fault Mutation Defense Audit</div>
        <div>Fault Type: <strong>${res.fault_type}</strong></div>
        <div>Description: ${res.description}</div>
        <div style="margin-top: 8px;">Server Defense Action: <code>${res.server_actual_response}</code></div>
        <div style="margin-top: 8px; font-weight: 700; color: var(--status-green);">${res.robustness_rating}</div>
      </div>
    `;
  }

  static async injectVersion() {
    const { host, port } = this.getTarget();
    const versionHex = '0x1A2B3C4D';
    const resArea = document.getElementById('inj-results-area');
    resArea.style.display = 'block';
    resArea.innerHTML = `<div style="padding: 14px;">⏳ Injecting custom version ${versionHex} to force Version Negotiation against ${host}:${port}...</div>`;

    const res = await ApiClient.runQUICInjectVersion(host, port, versionHex);
    resArea.innerHTML = `
      <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color);">
        <div style="font-weight: 700; font-size: 14px; margin-bottom: 6px; color: var(--primary-blue);">Version Negotiation Packet Verified</div>
        <div>Injected Version: <code>${res.injected_quic_version}</code></div>
        <div>Server Response Packet: <strong>${res.server_version_negotiation_packet.packet_type}</strong></div>
        <div style="margin-top: 6px; font-size: 12px;">Supported Server Versions: ${res.server_version_negotiation_packet.supported_versions.join(', ')}</div>
      </div>
    `;
  }
}
