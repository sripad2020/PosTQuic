class ProxyProfileView {
  static render(proxies = [], containerEl) {
    const list = proxies.map(p => `
      <tr style="background: var(--bg-surface);">
        <td><strong>${p.name}</strong></td>
        <td><span class="badge initial">${p.proxy_type}</span></td>
        <td><code>${p.host}:${p.port}</code></td>
        <td>${p.auth_type}</td>
        <td>${p.is_default ? '<strong>Yes (Default)</strong>' : 'No'}</td>
      </tr>
    `).join('');

    containerEl.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
        <div style="font-weight: 700; font-size: 16px;">Reusable Proxy Profile Manager</div>
      </div>

      <!-- ADD NEW PROXY FORM -->
      <div style="background: var(--bg-surface); padding: 16px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 20px;">
        <div style="font-weight: 700; margin-bottom: 12px; color: var(--primary-blue); font-size: 13px;">➕ Add Custom Proxy Profile</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 12px;">
          <div>
            <label style="display: block; font-weight: 600; margin-bottom: 4px;">Profile Name:</label>
            <input type="text" id="new-proxy-name" placeholder="e.g., My Custom SOCKS5 Proxy" style="width: 100%;">
          </div>
          <div>
            <label style="display: block; font-weight: 600; margin-bottom: 4px;">Proxy Type:</label>
            <select id="new-proxy-type" style="width: 100%;">
              <option value="SOCKS5">SOCKS5 (UDP Capable)</option>
              <option value="HTTP Proxy">HTTP Proxy</option>
              <option value="HTTPS / CONNECT Proxy">HTTPS / CONNECT Proxy</option>
              <option value="QUICLAB Agent Proxy">QUICLAB Agent Proxy</option>
            </select>
          </div>
          <div>
            <label style="display: block; font-weight: 600; margin-bottom: 4px;">Host / IP Address:</label>
            <input type="text" id="new-proxy-host" placeholder="e.g., 192.168.1.150" style="width: 100%;">
          </div>
          <div>
            <label style="display: block; font-weight: 600; margin-bottom: 4px;">Port:</label>
            <input type="number" id="new-proxy-port" value="1080" style="width: 100%;">
          </div>
          <div>
            <label style="display: block; font-weight: 600; margin-bottom: 4px;">Authentication:</label>
            <select id="new-proxy-auth" style="width: 100%;">
              <option value="None">None</option>
              <option value="Username/Password">Username / Password</option>
            </select>
          </div>
          <div>
            <label style="display: block; font-weight: 600; margin-bottom: 4px;">Username (Optional):</label>
            <input type="text" id="new-proxy-user" placeholder="Proxy Username" style="width: 100%;">
          </div>
        </div>
        <button class="btn-primary" style="padding: 7px 18px;" onclick="ProxyProfileView.saveCustomProxy()">Save Custom Proxy Profile</button>
      </div>

      <!-- EXISTING PROXIES TABLE -->
      <div style="font-weight: 700; margin-bottom: 8px; font-size: 13px;">Active Proxy Profiles (${proxies.length})</div>
      <table class="inspector-table" style="margin-bottom: 20px;">
        <thead>
          <tr>
            <th>Profile Name</th>
            <th>Type</th>
            <th>Endpoint</th>
            <th>Authentication</th>
            <th>Default</th>
          </tr>
        </thead>
        <tbody>${list}</tbody>
      </table>

      <!-- PRECEDENCE HIERARCHY -->
      <div style="background: var(--bg-muted); padding: 14px; border-radius: 6px;">
        <div style="font-weight: 700; margin-bottom: 6px;">Effective Proxy Precedence Hierarchy</div>
        <div style="font-family: var(--font-mono); font-size: 11.5px; color: var(--text-secondary);">
          Request Scope ➔ Session Scope ➔ Collection Scope ➔ Environment Scope ➔ Global Default
        </div>
      </div>
    `;
  }

  static async saveCustomProxy() {
    const name = document.getElementById('new-proxy-name')?.value;
    const proxy_type = document.getElementById('new-proxy-type')?.value;
    const host = document.getElementById('new-proxy-host')?.value;
    const port = parseInt(document.getElementById('new-proxy-port')?.value || '1080');
    const auth_type = document.getElementById('new-proxy-auth')?.value;
    const username = document.getElementById('new-proxy-user')?.value;

    if (!name || !host) {
      alert('Please enter a Profile Name and Host address for your proxy.');
      return;
    }

    const payload = {
      id: `proxy_${Date.now()}`,
      name: name,
      proxy_type: proxy_type,
      host: host,
      port: port,
      auth_type: auth_type,
      username: username
    };

    try {
      await ApiClient.saveProxy(payload);

      // Reload proxies and update top bar dropdown
      const updatedProxies = await ApiClient.fetchProxies();
      ProxyProfileView.render(updatedProxies, document.getElementById('view-other-container'));

      // Update Top Bar select-proxy element
      const proxySelect = document.getElementById('select-proxy');
      if (proxySelect) {
        const opt = document.createElement('option');
        opt.value = payload.id;
        opt.innerText = `${payload.name} (${payload.proxy_type})`;
        opt.selected = true;
        proxySelect.appendChild(opt);
        AppState.proxyProfileId = payload.id;
      }

      alert(`Proxy Profile "${name}" created successfully and selected!`);
    } catch (e) {
      alert(`Error saving proxy: ${e.message}`);
    }
  }
}
