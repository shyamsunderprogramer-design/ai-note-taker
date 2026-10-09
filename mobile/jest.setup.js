jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'));

jest.mock('react-native-webview', () => ({ WebView: require('react-native').View }));
jest.mock('react-native-safe-area-context', () =>
  require('react-native-safe-area-context/jest/mock').default);

jest.mock('react-native-audio-recorder-player', () => jest.fn().mockImplementation(() => ({
  startRecorder: jest.fn().mockResolvedValue('/tmp/test-recording.m4a'),
  stopRecorder: jest.fn().mockResolvedValue('/tmp/test-recording.m4a'),
  addRecordBackListener: jest.fn(),
  removeRecordBackListener: jest.fn(),
})));
// Jest has no native gesture bridge; preserve the surrounding navigation tree.
jest.mock('react-native-gesture-handler', () => {
  const { View, ScrollView, TouchableOpacity } = require('react-native');
  return {
    GestureHandlerRootView: View,
    PanGestureHandler: View,
    ScrollView,
    TouchableOpacity,
    State: { UNDETERMINED: 0, FAILED: 1, BEGAN: 2, CANCELLED: 3, ACTIVE: 4, END: 5 },
  };
});
// Use the native file-part representation, not Node's browser FormData.
global.FormData = require('react-native/Libraries/Network/FormData');
