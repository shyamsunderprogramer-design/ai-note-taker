// babel.config.js
// RN 0.73 requires this file at the project root for both Metro and Jest.
// The default preset chain is: @react-native/babel-preset + module:react-native-dotenv
// (the latter only if you need .env loading — drop it if you don't).
module.exports = {
  presets: ['module:@react-native/babel-preset'],
};
