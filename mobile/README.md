# ANT Mobile — React Native shell (Fix #27)

This is the **React Native** app for the AI Note Taker (ANT) project.
It runs on iOS and Android, talks to the FastAPI backend at
`backend/`, and is the third of the project's four deployment targets
(alongside the Electron desktop app, the Vite/React web SPA, and the
Chrome/browser extension).

## Folder layout

```
mobile/
├── app.json                # RN app registry metadata (name, displayName)
├── index.js                # AppRegistry entry point
├── package.json            # JS deps + jest config + npm scripts
├── babel.config.js         # Babel preset (@react-native/babel-preset)
├── metro.config.js         # Metro bundler config
├── .gitignore              # node_modules, build outputs, etc.
├── README.md               # ← you are here
│
├── src/                    # JavaScript application source
│   ├── App.js              # Top-level navigator (Login → Tabs)
│   └── services/           # Backend API + push notification clients
│       ├── api.js
│       └── notifications.js
│
├── __tests__/              # Jest tests (smoke + service tests)
│   ├── App.test.js
│   ├── api.test.js
│   └── notifications.test.js
│
├── ios/                    # iOS native project (Xcode) — added in Fix #27
│   ├── README.md           # how to build the iOS app
│   ├── Podfile             # CocoaPods manifest (Hermes enabled)
│   ├── .gitignore
│   └── "AI Note Taker"/
│       ├── AppDelegate.h
│       ├── AppDelegate.mm
│       ├── main.m
│       ├── Info.plist
│       ├── LaunchScreen.storyboard
│       └── Images.xcassets/
│   └── "AI Note Taker.xcodeproj"/
│       └── project.pbxproj
│
└── android/                # Android native project (Gradle) — added in Fix #27
    ├── README.md           # how to build the Android app
    ├── build.gradle
    ├── settings.gradle
    ├── gradle.properties
    ├── .gitignore
    └── app/
        ├── build.gradle
        ├── proguard-rules.pro
        └── src/main/
            ├── AndroidManifest.xml
            ├── java/com/ainotetaker/
            │   ├── MainActivity.kt
            │   └── MainApplication.kt
            └── res/values/
                ├── strings.xml
                └── styles.xml
```

## What's in this repo vs. a fresh `npx react-native init`

The audit (2026-06-05) found that `mobile/` was missing the native
project folders, so the app couldn't be built natively. Fix #27 added
the iOS and Android scaffolds, but in **hand-written, minimal form**:
- The `ios/AI Note Taker.xcodeproj/project.pbxproj` is a documented
  stub (see the file's header comment) — to produce a buildable
  project, regenerate it via Xcode or run the RN CLI template generator
  and diff. The other iOS files (`AppDelegate`, `Info.plist`, `Podfile`,
  `LaunchScreen.storyboard`, `Images.xcassets`) are real and correct for
  RN 0.73 + Hermes.
- The Android scaffold is real and correct for RN 0.73 + Hermes + the
  new architecture. The Gradle wrapper (`gradle/wrapper/` + `gradlew`)
  is intentionally omitted — generate it locally with
  `cd mobile/android && gradle wrapper --gradle-version 8.3` (it pulls
  a binary from `services.gradle.org` on first run, which we don't want
  in the repo).

The point of this scaffold: **the structure exists and is documented**,
so a contributor can `cd mobile && npm install && npx react-native upgrade`
to refresh, or open the folder in Xcode / Android Studio and let the
IDE generate the missing wrapper files.

## Running

From the repo root:

```bash
npm --workspace ant-mobile install   # one-time
npm run mobile:start                 # Metro bundler (in one terminal)
npm run mobile:ios                   # iOS Simulator (in another)
npm run mobile:android               # Android emulator (in another)
npm run mobile:test                  # Jest smoke tests
npm run mobile:lint                  # ESLint
```

The Android emulator hits the FastAPI backend at `http://10.0.2.2:8000`
(Android emulator's loopback to the host). The iOS simulator hits
`http://localhost:8000`. Both default URLs are in
`src/services/api.js`; override at runtime via AsyncStorage key
`api_url` (see `ApiService.init()`).

## Architecture (current)

The JS-side app is a 3-tab bottom navigator (Recordings / Conversations
/ Profile) wrapped in a stack navigator for login. Login talks to
`POST /auth/login`; the JWT is stored in AsyncStorage. The
Notifications service is currently a stub (the audit's "real" push
integration is deferred — see [[alembic-migrations-fix-23]] for the
comparable "intentionally stubbed, upgrade later" pattern).

The native side: this RN 0.73 project uses Hermes as the JS engine
and the new architecture (Fabric + TurboModules) by default — both are
toggled in the respective config files (`Podfile` for iOS,
`gradle.properties` for Android).
