/**
 * Push notification service for interview reminders.
 */
import { Platform } from "react-native"

class NotificationService {
  async requestPermissions() {
    // In a real app, integrate react-native-push-notification or
    // @react-native-firebase/messaging here.
    // Stub for now to keep build lightweight.
    return true
  }

  async scheduleInterviewReminder(title, date, body = "Interview starting soon") {
    // Stub — replace with native push scheduling once deps installed.
    console.log("[Notification] Scheduled:", title, date)
    return { id: "stub" }
  }

  async cancelAll() {
    console.log("[Notification] Cancelled all")
  }
}

export default new NotificationService()
