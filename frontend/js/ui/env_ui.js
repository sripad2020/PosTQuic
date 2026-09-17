class EnvironmentsView {
  static showSecrets = false;

  static async render(containerEl) {
    try {
      const fetchedEnvs = await ApiClient.fetchEnvironments();
      let envs = Array.isArray(fetchedEnvs) && fetchedEnvs.length > 0 ? fetchedEnvs : [
        { id: 'dev-env', name: 'Development', variables: '{"base_url": "http://127.0.0.1:8000", "quic_target": "quic.tech:4433", "proxy_host": "10.0.0.1", "auth_token": "bearer_dev_99182"}', is_active: 1 },
        { id: 'staging-env', name: 'Staging Lab', variables: '{"base_url": "https://staging.quiclab.io", "quic_target": "staging.quiclab.io:443", "proxy_host": "192.168.1.100", "auth_token": "bearer_stage_44210"}', is_active: 0 },
        { id: 'prod-env', name: 'Production QUIC Cloud', variables: '{"base_url": "https://cloudflare-quic.com", "quic_target": "cloudflare-quic.com:443", "proxy_host": "10.200.0.1", "auth_token": "bearer_prod_sec77"}', is_active: 0 }
      ];

      const activeEnv = envs.find(e => e.is_active) || envs[0];
      if (activeEnv) {
        try {
          AppState.envVars = typeof activeEnv.variables === 'string' ? JSON.parse(activeEnv.variables) : activeEnv.variables;
        } catch (e) {
          AppState.envVars = {};
        }
      }

      const envCards = envs.map(e => {
        let varsFormatted = '';
        try {
          const parsed = typeof e.variables === 'string' ? JSON.parse(e.variables) : e.variables;
          varsFormatted = Object.entries(parsed).map(([k, v]) => {
            const isSensitive = k.toLowerCase().includes('token') || k.toLowerCase().includes('pass') || k.toLowerCase().includes('secret') || k.toLowerCase().includes('key');
            const displayVal = (isSensitive && !EnvironmentsView.showSecrets) ? '••••••••••••' : v;

            return `
              <div style="display: flex; justify-content: space-between; font-family: var(--font-mono); font-size: 11.5px; border-bottom: 1px dotted var(--border-color); padding: 4px 0;">
                <span style="color: var(--primary-blue); font-weight: 600;">{{${k}}}</span>
                <span style="color: var(--text-primary); font-weight: ${isSensitive ? '700' : 'normal'};">${displayVal}</span>
              </div>
            `;
          }).join('');
        } catch (err) {
          varsFormatted = `<code>${e.variables}</code>`;
        }

        return `
          <div style="background: var(--bg-surface); padding: 14px; border-radius: 6px; border: 1px solid var(--border-color); margin-bottom: 14px; border-left: 4px solid ${e.is_active ? '#16A34A' : 'var(--border-color)'};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <div>
                <strong style="font-size: 14px; color: var(--text-primary);">${e.name}</strong>
                <span style="font-size: 11px; color: var(--text-muted); margin-left: 8px;">(ID: ${e.id})</span>
              </div>
              <div style="display: flex; gap: 8px; align-items: center;">
                <span class="badge ${e.is_active ? 'short' : 'initial'}">${e.is_active ? 'ACTIVE' : 'INACTIVE'}</span>
                ${!e.is_active ? `<button class="btn-run" style="font-size: 10px; padding: 2px 8px;" onclick="EnvironmentsView.activateEnv('${e.id}')">Set Active</button>` : ''}
                <button class="btn-secondary" style="font-size: 10px; padding: 2px 6px; color: var(--status-red);" onclick="EnvironmentsView.deleteEnv('${e.id}')">Delete</button>
              </div>
            </div>
            <div style="margin-top: 8px;">
              <label style="font-size: 11px; font-weight: 700; color: var(--text-muted); display: block; margin-bottom: 4px;">ENVIRONMENT VARIABLES:</label>
              ${varsFormatted}
            </div>
          </div>
        `;
      }).join('');

      containerEl.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <div>
            <div style="font-weight: 700; font-size: 16px; color: var(--primary-blue);">🌐 Environment Variables Manager</div>
            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
              Manage variable scopes (e.g., <code>{{base_url}}</code>, <code>{{quic_target}}</code>, <code>{{auth_token}}</code>) with masked security credentials.
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn-secondary" style="font-size: 11px; padding: 6px 12px;" id="btn-toggle-secrets">
              ${EnvironmentsView.showSecrets ? '🙈 Hide Secrets' : '👁️ Show Secrets'}
            </button>
            <button class="btn-secondary" style="font-size: 11px; padding: 6px 12px;" id="btn-add-env">+ Add New Environment</button>
          </div>
        </div>

        <!-- NEW ENVIRONMENT INLINE FORM (HIDDEN BY DEFAULT) -->
        <div id="form-new-env" style="display: none; background: var(--bg-surface); border: 1px solid var(--primary-blue); padding: 14px; border-radius: 6px; margin-bottom: 16px;">
          <h4 style="margin: 0 0 10px 0; color: var(--primary-blue);">Create New Environment Scope</h4>
          <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 10px; margin-bottom: 10px;">
            <div>
              <label style="font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px;">Environment Name:</label>
              <input type="text" id="input-env-name" placeholder="e.g. US-East Production" style="width: 100%; padding: 6px; font-size: 12px; border: 1px solid var(--border-color); border-radius: 4px;">
            </div>
            <div>
              <label style="font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px;">JSON Variables Dictionary:</label>
              <input type="text" id="input-env-vars" value='{"base_url": "https://api.target.com", "quic_target": "target.com:443", "auth_token": "secret_token_123"}' style="width: 100%; padding: 6px; font-size: 12px; font-family: var(--font-mono); border: 1px solid var(--border-color); border-radius: 4px;">
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn-run" style="font-size: 11px; padding: 4px 12px;" id="btn-save-env">Save Environment</button>
            <button class="btn-secondary" style="font-size: 11px; padding: 4px 12px;" onclick="document.getElementById('form-new-env').style.display='none'">Cancel</button>
          </div>
        </div>

        <div style="font-weight: 700; margin-bottom: 10px; font-size: 13px;">Configured Environments (${envs.length})</div>
        <div>${envCards}</div>
      `;

      const btnToggleSecrets = containerEl.querySelector('#btn-toggle-secrets');
      if (btnToggleSecrets) {
        btnToggleSecrets.addEventListener('click', () => {
          EnvironmentsView.showSecrets = !EnvironmentsView.showSecrets;
          EnvironmentsView.render(containerEl);
        });
      }

      const btnAddEnv = containerEl.querySelector('#btn-add-env');
      if (btnAddEnv) {
        btnAddEnv.addEventListener('click', () => {
          const form = containerEl.querySelector('#form-new-env');
          if (form) form.style.display = form.style.display === 'none' ? 'block' : 'none';
        });
      }

      const btnSaveEnv = containerEl.querySelector('#btn-save-env');
      if (btnSaveEnv) {
        btnSaveEnv.addEventListener('click', async () => {
          const name = containerEl.querySelector('#input-env-name')?.value || 'Custom Environment';
          const varsStr = containerEl.querySelector('#input-env-vars')?.value || '{}';
          await ApiClient.createEnvironment({ name: name, variables: varsStr, is_active: 0 });
          EnvironmentsView.render(containerEl);
        });
      }
    } catch (err) {
      console.error('Error rendering EnvironmentsView:', err);
      containerEl.innerHTML = `<div style="padding: 20px; color: red;">Failed to load environments: ${err.message}</div>`;
    }
  }

  static async activateEnv(envId) {
    await ApiClient.activateEnvironment(envId);
    const container = document.getElementById('view-other-container');
    if (container) EnvironmentsView.render(container);
  }

  static async deleteEnv(envId) {
    if (confirm(`Delete environment ${envId}?`)) {
      await ApiClient.deleteEnvironment(envId);
      const container = document.getElementById('view-other-container');
      if (container) EnvironmentsView.render(container);
    }
  }
}
