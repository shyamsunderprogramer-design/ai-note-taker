import Foundation
import Vision
import ImageIO

let data = FileHandle.standardInput.readDataToEndOfFile()
guard let source = CGImageSourceCreateWithData(data as CFData, nil),
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
    FileHandle.standardError.write(Data("Invalid image\n".utf8))
    exit(1)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
if #available(macOS 13.0, *) { request.automaticallyDetectsLanguage = true }
do {
    try VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
    let lines = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
    let output = try JSONSerialization.data(withJSONObject: ["text": lines.joined(separator: "\n")])
    FileHandle.standardOutput.write(output)
} catch {
    FileHandle.standardError.write(Data("Text recognition failed\n".utf8))
    exit(1)
}
