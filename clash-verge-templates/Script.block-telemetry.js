// Clash Verge Rev Global Script Template (profiles/Script.js)
// NOTE: Clash Verge Rev does NOT expand `prepend-rules:` inside Merge.yaml into `rules:`.
// Global rules MUST be injected via Script.js so they apply across all subscription profiles.

function main(config, profileName) {
  if (!config || !Array.isArray(config.rules)) return config;

  const prependRules = [
    'DOMAIN,localhost,DIRECT',
    'DOMAIN-SUFFIX,localhost,DIRECT',
    'IP-CIDR,127.0.0.0/8,DIRECT,no-resolve',
    'IP-CIDR6,::1/128,DIRECT,no-resolve',
    // Block Google Clearcut telemetry endpoint (`play.googleapis.com/log`) from looping uploads via proxy
    'DOMAIN,play.googleapis.com,REJECT'
  ];

  config.rules = [...prependRules, ...config.rules];
  return config;
}
