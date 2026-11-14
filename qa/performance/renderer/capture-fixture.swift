// Capture only the synthetic fixture region to disk. Display capture is cropped
// in memory before saving; other desktop contents are never written or printed.
import Foundation
import AppKit
import ScreenCaptureKit
import ImageIO
import UniformTypeIdentifiers
import CoreMedia
import CoreImage

func save(_ image: CGImage, to path: String) throws {
    guard let destination = CGImageDestinationCreateWithURL(URL(fileURLWithPath: path) as CFURL,
        UTType.png.identifier as CFString, 1, nil) else { throw NSError(domain: "ANT-QA", code: 3) }
    CGImageDestinationAddImage(destination, image, nil)
    guard CGImageDestinationFinalize(destination) else { throw NSError(domain: "ANT-QA", code: 4) }
}

final class FrameCollector: NSObject, SCStreamOutput, @unchecked Sendable {
    let crop: CGRect
    let context = CIContext()
    private let lock = NSLock()
    private var images: [CGImage] = []
    init(crop: CGRect) { self.crop = crop }
    func stream(_ stream: SCStream, didOutputSampleBuffer sample: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen, sample.isValid,
              let attachments = CMSampleBufferGetSampleAttachmentsArray(sample, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]],
              let status = attachments.first?[.status] as? Int, status == SCFrameStatus.complete.rawValue,
              let buffer = CMSampleBufferGetImageBuffer(sample) else { return }
        let input = CIImage(cvPixelBuffer: buffer)
        guard let full = context.createCGImage(input, from: input.extent),
              let image = full.cropping(to: crop) else { return }
        lock.lock(); defer { lock.unlock() }
        if images.count < 30 { images.append(image) }
    }
    func snapshot() -> [CGImage] { lock.lock(); defer { lock.unlock() }; return images }
}

@main struct CaptureFixture {
    @MainActor static func main() async throws {
        _ = NSApplication.shared
        _ = CGMainDisplayID()
        guard (3...4).contains(CommandLine.arguments.count),
              let pid = Int32(CommandLine.arguments[1]) else { exit(2) }
        let mode = CommandLine.arguments.count == 4 ? CommandLine.arguments[3] : "window"
        guard ["window", "display", "display-stream"].contains(mode) else { exit(2) }
        let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: false)
        guard let window = content.windows.first(where: {
            $0.owningApplication?.processID == pid && $0.title == "ANT Capture QA"
        }) else {
            let owned = content.windows.filter { $0.owningApplication?.processID == pid }
            let details = owned.map { "id=\($0.windowID),title=\($0.title ?? "nil"),onScreen=\($0.isOnScreen)" }.joined(separator: ";")
            throw NSError(domain: "ANT-QA", code: 1, userInfo: [NSLocalizedDescriptionKey: "Fixture missing; owned windows: " + details])
        }
        let config = SCStreamConfiguration()
        config.showsCursor = false
        let filter: SCContentFilter
        let crop: CGRect
        if mode == "window" {
            filter = SCContentFilter(desktopIndependentWindow: window)
            config.width = 640; config.height = 600
            crop = CGRect(x: 0, y: 0, width: 640, height: 600)
        } else {
            guard let display = content.displays.first(where: { $0.frame.contains(window.frame) }) else {
                throw NSError(domain: "ANT-QA", code: 5)
            }
            // No application/window exclusion supplied by the recorder.
            filter = SCContentFilter(display: display, excludingWindows: [])
            config.width = display.width; config.height = display.height
            let sx = Double(config.width) / display.frame.width
            let sy = Double(config.height) / display.frame.height
            crop = CGRect(x: (window.frame.minX - display.frame.minX) * sx,
                          y: (window.frame.minY - display.frame.minY) * sy,
                          width: window.frame.width * sx, height: window.frame.height * sy)
        }
        let output = CommandLine.arguments[2]
        if mode == "display-stream" {
            config.minimumFrameInterval = CMTime(value: 1, timescale: 15)
            config.queueDepth = 3
            let collector = FrameCollector(crop: crop)
            let stream = SCStream(filter: filter, configuration: config, delegate: nil)
            try stream.addStreamOutput(collector, type: .screen, sampleHandlerQueue: DispatchQueue(label: "ant.qa.capture"))
            try await stream.startCapture()
            try await Task.sleep(nanoseconds: 1_200_000_000)
            try await stream.stopCapture()
            let frames = collector.snapshot()
            guard !frames.isEmpty else { throw NSError(domain: "ANT-QA", code: 6) }
            for (index, frame) in frames.enumerated() { try save(frame, to: output + ".frame-\(index).png") }
            try save(frames.last!, to: output)
            print("{\"frames\":\(frames.count)}")
        } else {
            let full = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
            guard let image = full.cropping(to: crop) else { throw NSError(domain: "ANT-QA", code: 7) }
            try save(image, to: output)
        }
    }
}
