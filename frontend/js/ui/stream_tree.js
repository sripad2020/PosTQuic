class StreamTreeView {
  static render(streams = [], containerEl) {
    if (!streams || streams.length === 0) {
      containerEl.innerHTML = `<div style="padding: 20px; color: var(--text-muted);">No active QUIC streams available.</div>`;
      return;
    }

    const treeItems = streams.map(s => `
      <div class="tree-node active" style="margin-bottom: 12px; background: var(--bg-surface); padding: 10px; border-radius: 6px;">
        <div style="display: flex; justify-content: space-between; font-weight: 600;">
          <span>Stream ID: ${s.stream_id} (${s.type})</span>
          <span class="badge ${s.state === 'ACTIVE' ? 'short' : 'initial'}">${s.state}</span>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 8px; font-size: 11px; font-family: var(--font-mono);">
          <div>Direction: ${s.direction}</div>
          <div>Bytes Sent: ${s.bytes_sent} | Recv: ${s.bytes_received}</div>
          <div>Flow Control: ${s.flow_control}</div>
        </div>
      </div>
    `).join('');

    containerEl.innerHTML = `
      <div style="margin-bottom: 12px; font-weight: 700; font-size: 14px;">QUIC Connection Stream Hierarchy</div>
      <div style="border: 1px solid var(--border-color); padding: 14px; border-radius: 6px;">
        <div style="font-weight: 700; color: var(--primary-blue); margin-bottom: 10px;">Connection (Active QUIC Session)</div>
        ${treeItems}
      </div>
    `;
  }
}
