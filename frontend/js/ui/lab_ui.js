class NetworkLabView {
  static render(labConfig = {}, containerEl) {
    containerEl.innerHTML = `
      <div style="font-weight: 700; font-size: 15px; margin-bottom: 14px;">Network Laboratory & Impairment Emulation Engine</div>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
        <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-weight: 700; margin-bottom: 10px; color: var(--primary-blue);">Impairment Controls</div>
          <div style="display: flex; flex-direction: column; gap: 10px;">
            <div>
              <label>Latency (ms):</label>
              <input type="number" id="lab-latency" value="${labConfig.latency_ms || 25}" style="width: 100%;">
            </div>
            <div>
              <label>Jitter (ms):</label>
              <input type="number" id="lab-jitter" value="${labConfig.jitter_ms || 4.5}" style="width: 100%;">
            </div>
            <div>
              <label>Packet Loss (%):</label>
              <input type="number" step="0.1" id="lab-loss" value="${labConfig.packet_loss_pct || 0.5}" style="width: 100%;">
            </div>
            <div>
              <label>MTU Size (Bytes):</label>
              <input type="number" id="lab-mtu" value="${labConfig.mtu_bytes || 1472}" style="width: 100%;">
            </div>
          </div>
        </div>

        <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color);">
          <div style="font-weight: 700; margin-bottom: 10px; color: #16A34A;">QUIC Connection Migration Simulator</div>
          <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">
            Simulate dynamic network path switching while keeping active QUIC connections alive via PATH_CHALLENGE and PATH_RESPONSE frame validation.
          </p>
          
          <div style="display: flex; gap: 10px; margin-bottom: 14px;">
            <select id="migrate-from" style="flex: 1;">
              <option value="Wi-Fi" selected>Interface: Wi-Fi</option>
              <option value="Ethernet">Interface: Ethernet</option>
            </select>
            <span style="align-self: center;">➔</span>
            <select id="migrate-to" style="flex: 1;">
              <option value="5G" selected>Interface: 5G Cellular</option>
              <option value="4G">Interface: 4G LTE</option>
            </select>
          </div>

          <button class="btn-primary" style="width: 100%;" onclick="NetworkLabView.triggerMigration()">Trigger Network Path Migration</button>
          
          <div id="migration-result-box" style="margin-top: 14px; display: none;"></div>
        </div>
      </div>
    `;
  }

  static async triggerMigration() {
    const fromIface = document.getElementById('migrate-from').value;
    const toIface = document.getElementById('migrate-to').value;

    const res = await ApiClient.triggerLabMigration(fromIface, toIface);
    if (!res) return;

    const box = document.getElementById('migration-result-box');
    box.style.display = 'block';
    box.innerHTML = `
      <div class="route-box" style="background: #ECFDF5; border-color: #A7F3D0; color: #065F46;">
        <strong>Path Migration Validated:</strong> ${res.from_interface} ➔ ${res.to_interface}<br>
        • Frame: ${res.quic_path_validation.path_challenge.frame_type} (${res.quic_path_validation.path_challenge.data})<br>
        • Response: ${res.quic_path_validation.path_response.frame_type} (${res.quic_path_validation.path_response.data})<br>
        • Status: ${res.quic_path_validation.path_state} | RTT Probe: ${res.quic_path_validation.rtt_probe_ms} ms
      </div>
    `;
  }
}
