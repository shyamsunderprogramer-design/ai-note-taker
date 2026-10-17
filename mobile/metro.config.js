// metro.config.js
// Metro bundler config. RN 0.73 ships with sensible defaults; the @react-native/metro-config
// preset handles Hermes, SVG, and the asset registry.
const {getDefaultConfig, mergeConfig} = require('@react-native/metro-config');

/**
 * Metro configuration
 * https://reactnative.dev/docs/metro
 *
 * @type {import('metro-config').MetroConfig}
 */
const config = {};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);
