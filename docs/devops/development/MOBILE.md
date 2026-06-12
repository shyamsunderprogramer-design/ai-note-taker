# Mobile (React Native) Setup

> ANT's mobile app is a React Native 0.73 app that runs on iOS and Android. The native scaffolds are stubs — they have the right structure but you need to regenerate the platform-specific build files before the app will compile.

---

## 1. What's there

```
mobile/
├── src/
│   ├── App.js                       # 6+ screens, bottom-tab nav
│   ├── services/
│   │   ├── api.js                   # Axios client → backend
│   │   └── notifications.js
│   └── store/                       # zustand state (auth, conversations, settings)
│
├── __tests__/                       # Jest smoke tests (3)
│   ├── App.test.js
│   ├── api.test.js
│   └── notifications.test.js
│
├── ios/                             # iOS native scaffold
│   ├── AI Note Taker/               # AppDelegate.h, AppDelegate.mm, main.m
│   ├── AI Note Taker.xcodeproj/     # STUB — regenerate with `npx react-native upgrade`
│   ├── Podfile                      # Hermes enabled
│   └── README.md
│
├── android/                         # Android native scaffold (Kotlin)
│   ├── app/                         # MainActivity, MainApplication, AndroidManifest
│   ├── build.gradle
│   ├── settings.gradle
│   ├── gradle.properties            # new arch + Hermes enabled
│   └── README.md
│
├── app.json
├── index.js
├── babel.config.js
├── metro.config.js
├── package.json                     # RN 0.73, zustand, react-native-audio-recorder-player
└── README.md
```

The native scaffold files (Podfile, build.gradle, AppDelegate, etc.) are real and build-ready, EXCEPT for the gradle wrapper and the Xcode `.pbxproj` — those are platform-specific binaries that don't belong in the repo. Generate them locally.

---

## 2. Generate the missing build files

### iOS (macOS only)

```bash
cd mobile
npm install
# The .pbxproj is a stub. Regenerate it:
npx react-native upgrade  # picks up the latest RN template files
# Or open in Xcode and let it sync:
open ios/AI\ Note\ Taker.xcworkspace
# Xcode will offer to create a workspace + pod install.
```

### Android

```bash
cd mobile
npm install
# Generate the gradle wrapper (one-time, requires Java 17+)
gradle wrapper --gradle-version 8.3
# Or use the system gradle directly without the wrapper
```

Then open the `android/` folder in Android Studio — it will offer to download the missing SDKs and build tools automatically.

---

## 3. Run on a simulator

### iOS

```bash
make mobile-ios
# or:  cd mobile && npm run ios
```

This requires:
- macOS with Xcode 15+ installed
- An iOS Simulator (download from Xcode → Settings → Platforms)

### Android

```bash
make mobile-android
# or:  cd mobile && npm run android
```

This requires:
- Android Studio with at least one emulator image installed
- `ANDROID_HOME` env var set (Android Studio sets this for you)

---

## 4. Configure the backend URL

The mobile app talks to the backend over HTTP. In dev, the default URL is `http://10.0.2.2:8000` (Android emulator's loopback to the host) or `http://127.0.0.1:8000` (iOS simulator on macOS).

To change it at runtime: open the app → Settings → **API URL** → enter the new URL. The value is persisted with `AsyncStorage`.

To change it in code: edit `mobile/src/services/api.js` and rebuild.

For production, point it at the deployed Render URL: `https://ai-note-taker-7xvn.onrender.com`.

---

## 5. Audio recording

The mobile app uses `react-native-audio-recorder-player` for voice capture. To enable it:

1. iOS: add `NSMicrophoneUsageDescription` to `Info.plist` (already present in the scaffold).
2. Android: add `RECORD_AUDIO` permission to `AndroidManifest.xml` (already present in the scaffold).
3. Test on a physical device — emulator mic capture is unreliable.

For live streaming to the WebSocket transcription endpoint, use `@react-native-voice/voice` instead. The codebase uses Whisper over WebSocket, so this is the right choice if you need live captions.

---

## 6. State management

The app uses `zustand` (lightweight, no boilerplate) for global state. Three stores:

- `mobile/src/store/auth.js` — login state, JWT token, user profile
- `mobile/src/store/conversations.js` — cached conversation list
- `mobile/src/store/settings.js` — API URL, theme, notification prefs

State is in-memory only by default. For persistence across app restarts, use `react-native-mmkv` (fast, sync) or `@react-native-async-storage/async-storage` (async, already installed).

---

## 7. Tests

```bash
cd mobile && npm test
```

Currently 3 smoke tests:

- `App.test.js` — renders the app shell
- `api.test.js` — verifies the default API URL is the Android emulator loopback
- `notifications.test.js` — verifies the notification service stub

Add more as you build out the screens. Use `@testing-library/react-native` for component tests and `jest.mock('react-native-audio-recorder-player')` for audio lib mocks.

---

## 8. Push notifications

The scaffold has `react-native-push-notification` in `package.json` but no platform configuration yet. To enable:

### iOS

Add to `Info.plist`:
```xml
<key>UIBackgroundModes</key>
<array>
    <string>remote-notification</string>
</array>
```

Then set up APNs in Xcode → Capabilities.

### Android

Add to `AndroidManifest.xml`:
```xml
<receiver android:name="com.dieam.reactnativepushnotification.modules.RNPushNotificationPublisher"
          android:exported="false" />
```

Then set up FCM in Firebase Console.

For local notifications (no server), `react-native-push-notification` works out of the box.

---

## 9. Common gotchas

- **Metro bundler cache** — clear with `npx react-native start --reset-cache` if you see stale module errors.
- **CocoaPods install** — on iOS, run `cd ios && pod install` after every native dep change.
- **Gradle daemon** — on Android, `./gradlew --stop` to clear the daemon if builds are stuck.
- **New Architecture** — the scaffold enables the new arch (Fabric + TurboModules). If you hit compatibility issues with a library, disable it in `gradle.properties` (`newArchEnabled=false`) and `Podfile`.

---

## 10. Roadmap (not yet built)

The mobile app is currently a thin shell. To bring it to parity with the Electron desktop app:

- [ ] Live voice capture with `@react-native-voice/voice`
- [ ] Cognitive graph visualization screen
- [ ] Analytics dashboard
- [ ] Job tracker
- [ ] Resume review (with on-device OCR?)
- [ ] Study plan viewer
- [ ] Multi-provider AI chat (parity with desktop)
- [ ] Local-first sync (offline support via `react-native-mmkv`)
- [ ] Push notifications (FCM + APNs)
- [ ] Real auth flow (the current login screen is a stub)
- [ ] Test coverage expansion (currently 3 smoke tests)
