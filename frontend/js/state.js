const AppState = {
  currentTab: 'builder',
  protocol: 'HTTP/3',
  executionMode: 'Local',
  networkRoute: 'Existing Network',
  proxyProfileId: 'direct-profile',
  environmentId: 'dev-env',
  activeResult: null,
  
  config: {
    url: 'https://cloudflare-quic.com/',
    method: 'GET',
    headers: { 'User-Agent': 'QUICLAB/1.0' },
    body: ''
  },
  
  envVars: {
    base_url: 'http://127.0.0.1:8000',
    quic_target: 'quic.tech:4433'
  }
};
