# Android Build & Release

> **Role tag:** `devops`
> **Owner:** `role-devops`

---

## What goes here

Anything about building, signing, and shipping the React Native
Android app. The Android native project lives in
`mobile/android/` (added in the Phase 8 mobile extension, Fix #27).

---

## Local build

```bash
cd mobile/android
./gradlew assembleRelease

# Output: app/build/outputs/apk/release/app-release.apk
# Or AAB:
./gradlew bundleRelease
# Output: app/build/outputs/bundle/release/app-release.aab
```

## Code signing

- Keystore at `mobile/android/app/ant-release.keystore`
  (gitignored, only on the build machine).
- Credentials in `mobile/android/gradle.properties`
  (gitignored) — `ANT_UPLOAD_STORE_PASSWORD`, etc.
- `signingConfigs.release` in `app/build.gradle`.

## Play Store

- AAB upload via Google Play Console.
- Internal testing track for pre-release builds.
- Release notes per build (kept in
  `mobile/android/fastlane/metadata/` if Fastlane is set up).

---

## Known gotchas

- `minSdkVersion` is 24 (Android 7.0); lower devices can't install.
- `targetSdkVersion` follows the latest stable Android target
  (currently 34 / Android 14).
- ProGuard rules in `mobile/android/app/proguard-rules.pro` —
  React Native + native modules have specific keep rules.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
