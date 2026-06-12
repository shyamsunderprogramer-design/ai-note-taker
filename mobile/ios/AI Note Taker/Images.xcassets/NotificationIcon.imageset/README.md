# iOS Notification Icons

This asset catalog slot is for the **NotificationIcon** image set. As
of Phase 8 (2026-06-08), the slot is declared but the actual PNG files
are not present (this is a stub — the catalog references no images so
Xcode won't fail, but a real PNG is required to render notifications).

## How to add the icons

1. Generate the icon set using one of these methods:

   **a. From the master app icon** (recommended)
   ```bash
   # macOS — uses `sips` to resize
   for SIZE in 20 29 40 60; do
     for SCALE in 2 3; do
       PIXELS=$((SIZE * SCALE))
       sips -z $PIXELS $PIXELS /path/to/source/icon.png \
            --out "AI Note Taker/Images.xcassets/NotificationIcon.imageset/notification-icon-${SIZE}@${SCALE}x.png"
     done
   done
   ```

   **b. From a designed monochrome icon** (best for notifications —
   iOS tints it with the app's accent color)
   ```bash
   # Use any 1024×1024 PNG with a transparent background and white
   # foreground. iOS will tint it appropriately.
   ```

2. Edit `NotificationIcon.imageset/Contents.json` and uncomment the
   `filename` field for each size. The full set:
   - `notification-icon-20@2x.png` (40×40)
   - `notification-icon-20@3x.png` (60×60)
   - `notification-icon-29@2x.png` (58×58)
   - `notification-icon-29@3x.png` (87×87)
   - `notification-icon-40@2x.png` (80×80)
   - `notification-icon-40@3x.png` (120×120)
   - `notification-icon-60@2x.png` (120×120)
   - `notification-icon-60@3x.png` (180×180)

3. Reference the icon from your push notification config:
   ```js
   PushNotification.localNotification({
     title: "New Insight",
     message: "...",
     // iOS automatically uses the app's notification icon set
   })
   ```

## Why monochrome?

iOS tints notification icons with the app's accent color, so a
monochrome (black + transparent) source icon looks correct in both
light and dark mode. Don't use the full-color app icon — iOS will
display it at a small size and color details will be lost.
