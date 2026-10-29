// CI distribution configuration. Local builds keep the ad-hoc package.json config.
const { build } = require('./package.json');

const required = ['CSC_LINK', 'CSC_KEY_PASSWORD', 'APPLE_ID', 'APPLE_APP_SPECIFIC_PASSWORD', 'APPLE_TEAM_ID'];
const missing = required.filter(name => !process.env[name]?.trim());
if (missing.length) {
  throw new Error(`macOS releases require signing and notarization credentials: ${missing.join(', ')}. See docs/devops/deployment/MACOS_SIGNING.md`);
}
if (!/^[A-Z0-9]{10}$/.test(process.env.APPLE_TEAM_ID)) {
  throw new Error('APPLE_TEAM_ID must be the 10-character Apple Developer team ID');
}

module.exports = {
  ...build,
  forceCodeSigning: true,
  mac: {
    ...build.mac,
    // Empty identity enables discovery of the imported Developer ID certificate.
    identity: '',
    type: 'distribution',
    hardenedRuntime: true,
    notarize: true,
  },
};
