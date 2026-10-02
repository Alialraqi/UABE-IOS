import AVFoundation
import Foundation

struct AudioToolError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

enum AudioTools {

    static func toM4A(_ source: URL) async throws -> URL {
        let asset = AVURLAsset(url: source)
        guard let session = AVAssetExportSession(asset: asset, presetName: AVAssetExportPresetAppleM4A) else {
            throw AudioToolError(message: "This audio cannot be converted to M4A on this device.")
        }
        let name = source.deletingPathExtension().lastPathComponent
        let out = makeTempDir("UABEM4A").appendingPathComponent("\(name).m4a")
        session.outputURL = out
        session.outputFileType = .m4a
        await session.export()
        guard session.status == .completed else {
            throw session.error ?? AudioToolError(message: "M4A export failed.")
        }
        return out
    }

    static func toWAV(_ source: URL) async throws -> URL {
        let asset = AVURLAsset(url: source)
        let tracks = try await asset.loadTracks(withMediaType: .audio)
        guard let track = tracks.first else {
            throw AudioToolError(message: "No audio track found in this file.\nOgg/Vorbis files cannot be read by iOS - convert them to WAV, MP3 or M4A first.")
        }

        var rate = 44100.0
        var channels = 2
        if let desc = try await track.load(.formatDescriptions).first,
           let asbd = CMAudioFormatDescriptionGetStreamBasicDescription(desc)?.pointee {
            if asbd.mSampleRate > 0 { rate = asbd.mSampleRate }
            if asbd.mChannelsPerFrame > 0 { channels = Int(asbd.mChannelsPerFrame) }
        }
        channels = min(max(channels, 1), 2)

        let settings: [String: Any] = [
            AVFormatIDKey: kAudioFormatLinearPCM,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsBigEndianKey: false,
            AVLinearPCMIsNonInterleaved: false,
            AVSampleRateKey: rate,
            AVNumberOfChannelsKey: channels,
        ]
        let reader = try AVAssetReader(asset: asset)
        let output = AVAssetReaderTrackOutput(track: track, outputSettings: settings)
        guard reader.canAdd(output) else { throw AudioToolError(message: "Cannot read this audio track.") }
        reader.add(output)
        guard reader.startReading() else {
            throw reader.error ?? AudioToolError(message: "Cannot start reading the audio.")
        }

        var pcm = Data()
        while let buffer = output.copyNextSampleBuffer() {
            guard let block = CMSampleBufferGetDataBuffer(buffer) else { continue }
            let length = CMBlockBufferGetDataLength(block)
            var chunk = Data(count: length)
            let status = chunk.withUnsafeMutableBytes { raw -> OSStatus in
                guard let base = raw.baseAddress else { return -1 }
                return CMBlockBufferCopyDataBytes(block, atOffset: 0, dataLength: length, destination: base)
            }
            if status == kCMBlockBufferNoErr { pcm.append(chunk) }
        }
        if reader.status == .failed {
            throw reader.error ?? AudioToolError(message: "Audio decoding failed.")
        }
        guard !pcm.isEmpty else { throw AudioToolError(message: "The audio file is empty.") }

        let out = makeTempDir("UABEWav").appendingPathComponent("audio.wav")
        try wavData(pcm: pcm, channels: channels, rate: Int(rate)).write(to: out)
        return out
    }

    private static func wavData(pcm: Data, channels: Int, rate: Int) -> Data {
        func le32(_ v: Int) -> [UInt8] { (0..<4).map { UInt8((v >> (8 * $0)) & 0xFF) } }
        func le16(_ v: Int) -> [UInt8] { (0..<2).map { UInt8((v >> (8 * $0)) & 0xFF) } }
        let block = channels * 2
        var header = Data()
        header.append(contentsOf: Array("RIFF".utf8)); header.append(contentsOf: le32(36 + pcm.count))
        header.append(contentsOf: Array("WAVE".utf8))
        header.append(contentsOf: Array("fmt ".utf8)); header.append(contentsOf: le32(16))
        header.append(contentsOf: le16(1)); header.append(contentsOf: le16(channels))
        header.append(contentsOf: le32(rate)); header.append(contentsOf: le32(rate * block))
        header.append(contentsOf: le16(block)); header.append(contentsOf: le16(16))
        header.append(contentsOf: Array("data".utf8)); header.append(contentsOf: le32(pcm.count))
        return header + pcm
    }
}

final class AudioPlayerBox: NSObject, ObservableObject, AVAudioPlayerDelegate {
    @Published var playingURL: URL?
    private var player: AVAudioPlayer?

    func isPlaying(_ url: URL?) -> Bool {
        guard let url else { return false }
        return playingURL == url
    }

    func toggle(_ url: URL) {
        if playingURL == url { stop() } else { play(url) }
    }

    func play(_ url: URL) {
        stop()
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback)
            try AVAudioSession.sharedInstance().setActive(true)
            let p = try AVAudioPlayer(contentsOf: url)
            p.delegate = self
            p.play()
            player = p
            playingURL = url
        } catch {
            playingURL = nil
        }
    }

    func stop() {
        player?.stop()
        player = nil
        playingURL = nil
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        DispatchQueue.main.async { self.playingURL = nil }
    }
}
