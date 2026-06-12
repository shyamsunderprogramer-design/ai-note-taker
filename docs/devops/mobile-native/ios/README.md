# iOS Build & Release

> **Role tag:** `devops`
> **Owner:** `role-devops`

---

## What goes here

Anything about building, signing, notarizing, and shipping the
React Native iOS app. The iOS native project lives in
`mobile/ios/` (added in the Phase 8 mobile extension, Fix #27).

---

## Local build

```bash
cd mobile/ios
pod install
xcodebuild -workspace ANT.xcworkspace \
  -scheme ANT \
  -configuration Release \
  -archivePath build/ANT.xcarchive
```

## Code signing

- Apple Developer account credentials in
  `mobile/ios/AuthKey_*.p8` (gitignored).
- `match` (Fastlane) for cert/profile sync — see
  `mobile/ios/fastlane/Matchfile` (if present).
- Adhoc + App Store distribution profiles.

## Notarization

Required for macOS apps distributed outside the App Store. Use
`xcrun notarytool` with an App Store Connect API key.

## TestFlight / App Store

- TestFlight uploads via `xcrun altool --upload-package` or
  Transporter.
- App Store metadata lives in
  `mobile/ios/fastlane/metadata/` (if using Fastlane).

---

## Known gotchas

- CocoaPods version pinned in `mobile/ios/.ruby-version`.
- React Native autolinking requires
  `bundle exec pod install` after adding a new native module.
- Bitcode is disabled (deprecated by Apple as of Xcode 14).

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
