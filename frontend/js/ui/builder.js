class FormBuilder {
  static renderProtocolForm(protocol, containerEl) {
    let html = '';
    const p = protocol.upper ? protocol.upper() : protocol;

    if (p.includes('HTTP')) {
      html = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
          <div>
            <label style="font-weight: 600; display: block; margin-bottom: 4px;">Headers (JSON):</label>
            <textarea id="param-headers" rows="3" style="width: 100%; font-family: var(--font-mono);">{\n  "User-Agent": "QUICLAB/1.0"\n}</textarea>
          </div>
          <div>
            <label style="font-weight: 600; display: block; margin-bottom: 4px;">Request Body:</label>
            <textarea id="param-body" rows="3" style="width: 100%; font-family: var(--font-mono);" placeholder="Request body payload..."></textarea>
          </div>
        </div>

        <div style="background: var(--bg-muted); padding: 10px 12px; border-radius: 6px; border: 1px dashed var(--border-color);">
          <div style="font-weight: 700; font-size: 11.5px; color: #059669; margin-bottom: 8px;">🔒 Custom Server SSL Certificate & Client Certificate Header Configuration (File Upload Only)</div>
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
            <div>
              <label style="font-size: 11px; font-weight: 600; display: block;">Inject Required SSL Cert Header:</label>
              <select id="param-cert-header-type" style="width: 100%; font-size: 11.5px;">
                <option value="None">None (Standard Headers)</option>
                <option value="X-Client-Cert">X-Client-Cert (Public PEM)</option>
                <option value="X-SSL-Cert">X-SSL-Cert (Cert Content)</option>
                <option value="X-Forwarded-Client-Cert">X-Forwarded-Client-Cert (SAN/Hash)</option>
              </select>
            </div>
            <div>
              <label style="font-size: 11px; font-weight: 600; display: block;">Upload Public Cert (.crt / .pem):</label>
              <input type="file" id="param-client-cert-file" accept=".crt,.pem,.cer,.p12" style="width: 100%; font-size: 11px; background: var(--bg-surface); padding: 4px; border: 1px solid var(--border-color); border-radius: 4px;">
            </div>
            <div>
              <label style="font-size: 11px; font-weight: 600; display: block;">Upload Private Key (.key / .pem):</label>
              <input type="file" id="param-client-key-file" accept=".key,.pem" style="width: 100%; font-size: 11px; background: var(--bg-surface); padding: 4px; border: 1px solid var(--border-color); border-radius: 4px;">
            </div>
          </div>
        </div>
      `;
    } else if (p.includes('QUIC')) {
      html = `
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
          <div>
            <label style="font-weight: 600; display: block;">Target Host:</label>
            <input type="text" id="param-host" value="quic.tech" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Port:</label>
            <input type="number" id="param-port" value="4433" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">ALPN Protocol Token <span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">(h3, doq, transport)</span>:</label>
            <input type="text" id="param-alpn" value="h3" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">SNI Hostname <span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">(TLS Server Name Indication)</span>:</label>
            <input type="text" id="param-sni" value="quic.tech" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">0-RTT Early Data <span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">(Session Ticket Reuse)</span>:</label>
            <select id="param-zerortt" style="width: 100%;">
              <option value="false">Disabled</option>
              <option value="true">Enable 0-RTT</option>
            </select>
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Path Migration <span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">(IP/Port Change)</span>:</label>
            <select id="param-migration" style="width: 100%;">
              <option value="true">Supported</option>
              <option value="false">Disabled</option>
            </select>
          </div>
        </div>
      `;
    } else if (p.includes('TCP')) {
      html = `
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
          <div>
            <label style="font-weight: 600; display: block;">Target Host:</label>
            <input type="text" id="param-host" value="127.0.0.1" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Port:</label>
            <input type="number" id="param-port" value="80" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Payload Mode:</label>
            <select id="param-payload-mode" style="width: 100%;">
              <option value="Text">Plain Text</option>
              <option value="Hex">Hexadecimal</option>
              <option value="Base64">Base64</option>
            </select>
          </div>
        </div>
        <div style="margin-top: 10px;">
          <label style="font-weight: 600; display: block;">TCP Payload:</label>
          <input type="text" id="param-payload" value="PING TCP SOCKET" style="width: 100%; font-family: var(--font-mono);">
        </div>
      `;
    } else if (p.includes('UDP')) {
      html = `
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 10px;">
          <div>
            <label style="font-weight: 600; display: block;">Destination IP:</label>
            <input type="text" id="param-host" value="127.0.0.1" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Port:</label>
            <input type="number" id="param-port" value="53" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Packet Count:</label>
            <input type="number" id="param-count" value="5" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Packet Size (Bytes):</label>
            <input type="number" id="param-size" value="64" style="width: 100%;">
          </div>
        </div>
      `;
    } else if (p.includes('DNS')) {
      html = `
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
          <div>
            <label style="font-weight: 600; display: block;">Target Domain:</label>
            <input type="text" id="param-domain" value="google.com" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Query Record Type:</label>
            <select id="param-record" style="width: 100%;">
              <option value="A">A (IPv4)</option>
              <option value="AAAA">AAAA (IPv6)</option>
              <option value="MX">MX (Mail Exchange)</option>
              <option value="TXT">TXT (Text/SPF)</option>
              <option value="CAA">CAA (Certificate Authority)</option>
            </select>
          </div>
          <div>
            <label style="font-weight: 600; display: block;">DNS Transport:</label>
            <select id="param-dnstransport" style="width: 100%;">
              <option value="UDP">UDP</option>
              <option value="TCP">TCP</option>
              <option value="DoH">DNS-over-HTTPS (DoH)</option>
            </select>
          </div>
        </div>
      `;
    } else if (p.includes('OPENSSL')) {
      html = `
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 10px;">
          <div>
            <label style="font-weight: 600; display: block;">Target Host / IP:</label>
            <input type="text" id="param-host" value="cloudflare.com" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Port:</label>
            <input type="number" id="param-port" value="443" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">SNI Hostname <span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">(TLS Server Name)</span>:</label>
            <input type="text" id="param-sni" value="cloudflare.com" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">TLS Version Constraint:</label>
            <select id="param-tlsver" style="width: 100%;">
              <option value="TLS 1.3">TLS 1.3</option>
              <option value="TLS 1.2">TLS 1.2</option>
            </select>
          </div>
        </div>
      `;
    } else {
      html = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <div>
            <label style="font-weight: 600; display: block;">Target Host:</label>
            <input type="text" id="param-host" value="127.0.0.1" style="width: 100%;">
          </div>
          <div>
            <label style="font-weight: 600; display: block;">Port:</label>
            <input type="number" id="param-port" value="22" style="width: 100%;">
          </div>
        </div>
      `;
    }

    containerEl.innerHTML = html;
  }

  static getConfigFromForm(protocol) {
    const p = protocol.upper ? protocol.upper() : protocol;
    const cfg = {};

    if (p.includes('HTTP')) {
      cfg.url = document.getElementById('input-url').value;
      cfg.method = document.getElementById('select-method').value;
      try {
        cfg.headers = JSON.parse(document.getElementById('param-headers')?.value || '{}');
      } catch (e) {
        cfg.headers = {};
      }
      cfg.body = document.getElementById('param-body')?.value || '';
      cfg.cert_header_type = document.getElementById('param-cert-header-type')?.value || 'None';
      cfg.client_cert = document.getElementById('param-client-cert-file')?.files[0]?.name || '';
      cfg.client_key = document.getElementById('param-client-key-file')?.files[0]?.name || '';
    } else if (p.includes('QUIC')) {
      cfg.host = document.getElementById('param-host')?.value || 'quic.tech';
      cfg.port = parseInt(document.getElementById('param-port')?.value || '4433');
      cfg.alpn = document.getElementById('param-alpn')?.value || 'h3';
      cfg.sni = document.getElementById('param-sni')?.value || cfg.host;
    } else if (p.includes('TCP')) {
      cfg.host = document.getElementById('param-host')?.value || '127.0.0.1';
      cfg.port = parseInt(document.getElementById('param-port')?.value || '80');
      cfg.payload = document.getElementById('param-payload')?.value || 'PING';
      cfg.payload_mode = document.getElementById('param-payload-mode')?.value || 'Text';
    } else if (p.includes('UDP')) {
      cfg.host = document.getElementById('param-host')?.value || '127.0.0.1';
      cfg.port = parseInt(document.getElementById('param-port')?.value || '53');
      cfg.packet_count = parseInt(document.getElementById('param-count')?.value || '5');
      cfg.packet_size = parseInt(document.getElementById('param-size')?.value || '64');
    } else if (p.includes('DNS')) {
      cfg.domain = document.getElementById('param-domain')?.value || 'google.com';
      cfg.record_type = document.getElementById('param-record')?.value || 'A';
      cfg.dns_transport = document.getElementById('param-dnstransport')?.value || 'UDP';
    } else if (p.includes('OPENSSL')) {
      cfg.host = document.getElementById('param-host')?.value || 'cloudflare.com';
      cfg.port = parseInt(document.getElementById('param-port')?.value || '443');
      cfg.sni = document.getElementById('param-sni')?.value || cfg.host;
      cfg.tls_version = document.getElementById('param-tlsver')?.value || 'TLS 1.3';
    } else {
      cfg.host = document.getElementById('param-host')?.value || '127.0.0.1';
      cfg.port = parseInt(document.getElementById('param-port')?.value || '22');
    }

    return cfg;
  }
}
