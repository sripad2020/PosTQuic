document.addEventListener('DOMContentLoaded', async () => {
  const protocolSelect = document.getElementById('select-protocol');
  const methodSelect = document.getElementById('select-method');
  const executionSelect = document.getElementById('select-execution');
  const networkSelect = document.getElementById('select-network');
  const proxySelect = document.getElementById('select-proxy');
  const formFieldsContainer = document.getElementById('dynamic-form-fields');
  const previewBox = document.getElementById('effective-route-preview');
  const runBtn = document.getElementById('btn-run-request');

  // Initial Form rendering & Proxy Loading
  FormBuilder.renderProtocolForm(protocolSelect.value, formFieldsContainer);
  loadProxyOptions();
  loadEnvironmentOptions();
  updateRoutePreview();

  async function loadEnvironmentOptions() {
    const envSelect = document.getElementById('select-env');
    if (!envSelect) return;
    const envs = await ApiClient.fetchEnvironments();
    if (envs && envs.length > 0) {
      envSelect.innerHTML = envs.map(e => `
        <option value="${e.id}" ${e.is_active ? 'selected' : ''}>${e.name}</option>
      `).join('');
      
      const active = envs.find(e => e.is_active) || envs[0];
      try {
        AppState.envVars = typeof active.variables === 'string' ? JSON.parse(active.variables) : active.variables;
      } catch (err) { AppState.envVars = {}; }
    }

    envSelect.addEventListener('change', (e) => {
      const selectedId = e.target.value;
      const found = envs.find(ev => ev.id === selectedId);
      if (found) {
        try {
          AppState.envVars = typeof found.variables === 'string' ? JSON.parse(found.variables) : found.variables;
        } catch (err) { AppState.envVars = {}; }
      }
    });
  }

  async function loadProxyOptions() {
    const proxies = await ApiClient.fetchProxies();
    if (proxies && proxies.length > 0 && proxySelect) {
      proxySelect.innerHTML = proxies.map(p => `
        <option value="${p.id}">${p.name} (${p.proxy_type})</option>
      `).join('');
      AppState.proxyProfileId = proxySelect.value;
    }
  }

  // Event Listeners for selectors
  protocolSelect.addEventListener('change', (e) => {
    AppState.protocol = e.target.value;
    
    // Update Workspace Tab Header Title
    const tabTitleEl = document.getElementById('tab-title-active');
    if (tabTitleEl) {
      tabTitleEl.innerText = `Active Request (${AppState.protocol})`;
    }

    const urlInput = document.getElementById('input-url');

    if (AppState.protocol.includes('HTTP')) {
      methodSelect.style.display = 'inline-block';
      if (urlInput) urlInput.style.display = 'inline-block';
    } else if (AppState.protocol === 'WEBSOCKET') {
      methodSelect.style.display = 'none';
      if (urlInput) {
        urlInput.style.display = 'inline-block';
        urlInput.value = 'wss://echo.websocket.events';
      }
    } else {
      methodSelect.style.display = 'none';
      if (urlInput) urlInput.style.display = 'none';
    }

    FormBuilder.renderProtocolForm(AppState.protocol, formFieldsContainer);
    validateRouteCompatibility();
    updateRoutePreview();
  });

  executionSelect.addEventListener('change', (e) => {
    AppState.executionMode = e.target.value;
    const statusText = document.getElementById('agent-status-text');
    if (AppState.executionMode === 'QUICLAB Agent') {
      statusText.innerText = 'Agent: 127.0.0.1:9000 (Connected)';
    } else {
      statusText.innerText = 'Local FastAPI Engine Active';
    }
    validateRouteCompatibility();
    updateRoutePreview();
  });

  networkSelect.addEventListener('change', (e) => {
    AppState.networkRoute = e.target.value;
    validateRouteCompatibility();
    updateRoutePreview();
  });

  proxySelect.addEventListener('change', (e) => {
    AppState.proxyProfileId = e.target.value;
    validateRouteCompatibility();
    updateRoutePreview();
  });

  // Sidebar Tab Switching
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', async () => {
      navItems.forEach(n => n.classList.remove('active'));
      item.classList.add('active');

      const tab = item.getAttribute('data-tab');
      AppState.currentTab = tab;
      
      const builderView = document.getElementById('view-request-builder');
      const otherView = document.getElementById('view-other-container');

      if (tab === 'builder') {
        builderView.style.display = 'block';
        otherView.style.display = 'none';
      } else {
        builderView.style.display = 'none';
        otherView.style.display = 'block';

        if (tab === 'overview') {
          OverviewGuideView.render(otherView);
        } else if (tab === 'quic-inspector') {
          QUICInspectorView.render(AppState.activeResult?.quic_details?.packets || [], otherView);
        } else if (tab === 'stream-tree') {
          StreamTreeView.render(AppState.activeResult?.quic_details?.streams || [], otherView);
        } else if (tab === 'adv-quic') {
          AdvQUICView.render(otherView);
        } else if (tab === 'quic-injector-studio') {
          QUICInjectorStudioView.render(otherView);
        } else if (tab === 'quic-perf-studio') {
          QUICPerfStudioView.render(otherView);
        } else if (tab === 'correlation') {
          CorrelationView.render(AppState.activeResult?.correlation || null, otherView);
        } else if (tab === 'network-lab') {
          const cfg = await ApiClient.fetchLabConfig();
          NetworkLabView.render(cfg, otherView);
        } else if (tab === 'mesh-topology') {
          MeshView.render(otherView);
        } else if (tab === 'openssl-studio') {
          OpenSSLStudioView.render(otherView);
        } else if (tab === 'proxy-manager') {
          const proxies = await ApiClient.fetchProxies();
          ProxyProfileView.render(proxies, otherView);
        } else if (tab === 'fuzzer') {
          FuzzerView.render(otherView);
        } else if (tab === 'stress-runner') {
          StressView.render(otherView);
        } else if (tab === 'sessions') {
          SessionsView.render(otherView);
        } else if (tab === 'environments') {
          EnvironmentsView.render(otherView);
        } else if (tab === 'collections') {
          CollectionsView.render(otherView);
        } else if (tab === 'network-vis') {
          NetworkVisView.render(otherView);
        } else if (tab === 'effective-route') {
          EffectiveRouteView.render(otherView);
        } else {
          otherView.innerHTML = `<div style="padding: 20px;"><strong>${tab.toUpperCase()} View Active</strong></div>`;
        }
      }
    });
  });

  // Workspace Tabs Click Listeners (Active Request vs Effective Route Preview)
  const tabActiveReq = document.getElementById('tab-title-active');
  const tabEffectiveRoute = document.getElementById('tab-route-effective');
  const previewBoxEl = document.getElementById('effective-route-preview');
  const builderViewEl = document.getElementById('view-request-builder');
  const otherViewEl = document.getElementById('view-other-container');

  if (tabActiveReq && tabEffectiveRoute) {
    tabActiveReq.addEventListener('click', () => {
      tabActiveReq.classList.add('active');
      tabEffectiveRoute.classList.remove('active');
      builderViewEl.style.display = 'block';
      otherViewEl.style.display = 'none';
    });

    tabEffectiveRoute.addEventListener('click', () => {
      tabEffectiveRoute.classList.add('active');
      tabActiveReq.classList.remove('active');
      builderViewEl.style.display = 'none';
      otherViewEl.style.display = 'block';
      EffectiveRouteView.render(otherViewEl);
    });
  }

  if (previewBoxEl) {
    previewBoxEl.style.cursor = 'pointer';
    previewBoxEl.title = 'Click to open Interactive Effective Route Inspector';
    previewBoxEl.addEventListener('click', () => {
      if (tabEffectiveRoute) tabEffectiveRoute.click();
    });
  }

  // Response View Toggle Buttons (JSON vs Rendered HTML Web View)
  const btnJson = document.getElementById('btn-resp-json');
  const btnHtml = document.getElementById('btn-resp-html');
  const jsonContainer = document.getElementById('response-body-content');
  const htmlContainer = document.getElementById('response-html-preview');
  const iframeEl = document.getElementById('html-preview-frame');

  if (btnJson && btnHtml) {
    btnJson.addEventListener('click', () => {
      btnJson.style.background = '#FFF';
      btnJson.style.fontWeight = '600';
      btnHtml.style.background = 'transparent';
      btnHtml.style.fontWeight = 'normal';

      jsonContainer.style.display = 'block';
      htmlContainer.style.display = 'none';
    });

    btnHtml.addEventListener('click', () => {
      btnHtml.style.background = '#FFF';
      btnHtml.style.fontWeight = '600';
      btnJson.style.background = 'transparent';
      btnJson.style.fontWeight = 'normal';

      jsonContainer.style.display = 'none';
      htmlContainer.style.display = 'block';

      // Load HTML content into iframe
      let htmlBody = AppState.activeResult?.body || AppState.activeResult?.correlation?.application_layer?.body_preview || '';
      if (!htmlBody || !htmlBody.includes('<')) {
        htmlBody = `<!DOCTYPE html><html><body style="font-family: sans-serif; padding: 20px; color: #475569;">
          <h3>No Renderable HTML Response</h3>
          <p>The response payload is plain JSON or binary raw data. Switch back to <strong>JSON / Raw</strong> view to inspect details.</p>
        </body></html>`;
      }
      iframeEl.srcdoc = htmlBody;
    });
  }

  // Execute Request Button Handler
  runBtn.addEventListener('click', async () => {
    runBtn.disabled = true;
    runBtn.innerText = '⏳ Executing...';

    const cfg = FormBuilder.getConfigFromForm(AppState.protocol);
    
    const payload = {
      protocol: AppState.protocol,
      execution_mode: AppState.executionMode,
      network_route: AppState.networkRoute,
      proxy_profile_id: AppState.proxyProfileId,
      config: cfg,
      env_vars: AppState.envVars
    };

    const res = await ApiClient.executeRequest(payload);
    runBtn.disabled = false;
    runBtn.innerText = '▶ Run Request';

    if (!res) return;

    if (!res.success && res.status === 'PROXY INCOMPATIBLE') {
      showProxyIncompatibleAlert(res.error);
      return;
    }

    AppState.activeResult = res.result;

    // Record Session History Item
    if (!AppState.sessionsHistory) AppState.sessionsHistory = [];
    AppState.sessionsHistory.unshift({
      session_id: res.session?.session_id || 's_' + Math.random().toString(16).substring(2, 8),
      protocol: AppState.protocol,
      target: document.getElementById('input-url')?.value || document.getElementById('param-host')?.value || 'Target',
      execution_mode: AppState.executionMode,
      state: res.success ? 'CLOSED' : 'FAILED',
      rtt_ms: res.result?.metrics?.latest_rtt_ms || res.result?.rtt_ms || 21.4,
      timestamp: new Date().toLocaleTimeString()
    });

    // Update Response UI
    const statusBadge = document.getElementById('response-status-badge');
    const rttText = document.getElementById('response-rtt-text');
    const bodyView = document.getElementById('response-body-content');

    if (res.success) {
      statusBadge.className = 'badge short';
      statusBadge.innerText = res.result.status_code || res.result.status || '200 OK';
      rttText.innerText = `RTT: ${res.result.metrics?.latest_rtt_ms || res.result.rtt_ms || 21.4} ms | Transferred: ${res.result.metrics?.bytes_received || 1024} bytes`;
      
      const aiRes = await ApiClient.runAiDiagnostics(res.result);
      const aiInsights = (aiRes.insights || []).map(i => `
        <div style="font-size: 11.5px; margin-top: 4px;">
          <strong>[${i.category}] ${i.title}:</strong> ${i.detail}
        </div>
      `).join('');

      bodyView.innerHTML = `
        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px; color: #166534; font-family: var(--font-sans);">
          <div style="font-weight: 700; font-size: 12px; display: flex; justify-content: space-between; align-items: center;">
            <span>🤖 AI Protocol Security & Performance Audit</span>
            <span>Security Score: ${aiRes.security_score}/100 | Perf Score: ${aiRes.performance_score}/100</span>
          </div>
          ${aiInsights}
        </div>
        <pre style="margin: 0; font-family: var(--font-mono);">${JSON.stringify(res.result, null, 2)}</pre>
      `;

      // Auto load iframe content if HTML present
      const rawHtml = res.result.body || res.result.correlation?.application_layer?.body_preview;
      if (rawHtml && iframeEl) {
        iframeEl.srcdoc = rawHtml;
      }
    } else {
      statusBadge.className = 'badge initial';
      statusBadge.innerText = 'FAILED';
      bodyView.innerText = JSON.stringify(res.error || res, null, 2);
    }
  });

  // Helper functions
  async function validateRouteCompatibility() {
    const payload = {
      protocol: AppState.protocol,
      execution_mode: AppState.executionMode,
      network_route: AppState.networkRoute,
      proxy_profile_id: AppState.proxyProfileId
    };

    const res = await ApiClient.validateCompatibility(payload);
    if (!res.compatible) {
      showProxyIncompatibleAlert(res.error_details);
    }
  }

  function showProxyIncompatibleAlert(err) {
    if (!err) return;
    const bodyView = document.getElementById('response-body-content');
    const statusBadge = document.getElementById('response-status-badge');
    
    statusBadge.className = 'badge initial';
    statusBadge.innerText = 'PROXY INCOMPATIBLE';

    bodyView.innerHTML = `
      <div style="color: var(--status-red); background: var(--status-red-bg); padding: 14px; border-radius: 6px; font-family: var(--font-sans);">
        <h3 style="margin-bottom: 8px;">PROXY INCOMPATIBLE</h3>
        <p><strong>Selected Protocol:</strong> ${err.protocol}</p>
        <p><strong>Configured Proxy:</strong> ${err.proxy_name} (${err.proxy_type})</p>
        <p style="margin-top: 8px;"><strong>Reason:</strong> ${err.reason}</p>
        <p style="margin-top: 8px;"><strong>Action:</strong> ${err.action}</p>
      </div>
    `;
  }

  function updateRoutePreview() {
    let targetStr = document.getElementById('input-url')?.value;
    if (!targetStr || document.getElementById('input-url')?.style.display === 'none') {
      targetStr = document.getElementById('param-host')?.value || document.getElementById('param-domain')?.value || 'quic.tech:4433';
    }
    const proxyName = proxySelect.options[proxySelect.selectedIndex]?.text || 'Direct';
    const netStr = AppState.networkRoute === 'Configured Proxy' ? `Proxy (${proxyName})` : 'Existing Network';
    
    previewBox.innerText = `UI ↓ Execution (${AppState.executionMode}) ↓ Route (${netStr}) ↓ Protocol (${AppState.protocol}) ↓ Target (${targetStr})`;
  }

  // Initialize WebSockets
  ApiClient.initWebSockets((metrics) => {
    document.getElementById('metrics-rtt').innerText = `${metrics.rtt_ms} ms`;
    document.getElementById('metrics-throughput').innerText = `${metrics.throughput_mbps} Mbps`;
    document.getElementById('metrics-packets').innerText = `${metrics.packets_total}`;
    document.getElementById('metrics-streams').innerText = `${metrics.active_streams} active`;
  });
});
