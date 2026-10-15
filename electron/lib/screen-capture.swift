import Foundation
import ScreenCaptureKit
import AppKit
import ImageIO
import UniformTypeIdentifiers

@main
struct CaptureScreen {
    static func main() async {
        do {
            guard #available(macOS 14.0, *) else {
                throw NSError(domain: "ANTCapture", code: 1, userInfo: [NSLocalizedDescriptionKey: "Screen capture requires macOS 14 or later."])
            }
            guard CommandLine.arguments.count == 3,
                  let excludedPID = Int32(CommandLine.arguments[1]),
                  let displayID = UInt32(CommandLine.arguments[2]) else {
                throw NSError(domain: "ANTCapture", code: 2)
            }
            let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
            guard let display = content.displays.first(where: { $0.displayID == (displayID == 0 ? CGMainDisplayID() : displayID) }) else {
                throw NSError(domain: "ANTCapture", code: 3, userInfo: [NSLocalizedDescriptionKey: "The selected display is unavailable."])
            }
            let excluded = content.applications.filter { $0.processID == excludedPID }
            guard !excluded.isEmpty else {
                throw NSError(domain: "ANTCapture", code: 6, userInfo: [NSLocalizedDescriptionKey: "ANT could not be identified for capture exclusion."])
            }
            let filter = SCContentFilter(display: display, excludingApplications: excluded, exceptingWindows: [])
            let config = SCStreamConfiguration()
            let scale = min(1.0, 1920.0 / Double(display.width))
            config.width = max(1, Int(Double(display.width) * scale))
            config.height = max(1, Int(Double(display.height) * scale))
            config.showsCursor = false
            let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
            let data = NSMutableData()
            guard let destination = CGImageDestinationCreateWithData(data, UTType.jpeg.identifier as CFString, 1, nil) else {
                throw NSError(domain: "ANTCapture", code: 4)
            }
            CGImageDestinationAddImage(destination, image, [kCGImageDestinationLossyCompressionQuality: 0.85] as CFDictionary)
            guard CGImageDestinationFinalize(destination) else { throw NSError(domain: "ANTCapture", code: 5) }
            FileHandle.standardOutput.write(data as Data)
        } catch {
            FileHandle.standardError.write(Data("Screen capture failed: \(error.localizedDescription)\n".utf8))
            exit(1)
        }
    }
}
