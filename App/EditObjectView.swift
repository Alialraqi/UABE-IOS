import SwiftUI
import UniformTypeIdentifiers

struct EditObjectView: View {
    let item: ObjectItem
    @EnvironmentObject var vm: BundleViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var loading = true
    @State private var loadError: String?
    @State private var info: ObjectDataInfo?
    @State private var meshURL: URL?
    @State private var image: UIImage?
    @State private var text = ""
    @State private var readOnlyReason: String?
    @State private var saving = false
    @State private var localError: String?
    @State private var exportItem: ExportItem?
    @State private var audioURL: URL?
    @State private var pendingWAV: URL?
    @StateObject private var player = AudioPlayerBox()

    var body: some View {
        NavigationStack {
            Group {
                if loading {
                    ProgressView("Loading…")
                } else if let loadError {
                    VStack(spacing: 12) {
                        Image(systemName: "exclamationmark.triangle").font(.largeTitle).foregroundColor(.orange)
                        Text("Failed to load data").font(.headline)
                        Text(loadError).font(.footnote).foregroundStyle(.secondary).multilineTextAlignment(.center)
                    }
                    .padding()
                } else if let info {
                    content(for: info)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .navigationTitle(item.name.isEmpty ? "Edit Object" : item.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
                ToolbarItem(placement: .primaryAction) {
                    if info != nil {
                        Button {
                            Task {
                                if let url = await vm.exportObject(item) { exportItem = ExportItem(url: url) }
                            }
                        } label: { Image(systemName: "square.and.arrow.up") }
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    if let info, isTextual(info), readOnlyReason == nil {
                        Button(saving ? "Saving…" : "Save") { Task { await save(info) } }
                            .disabled(saving)
                    }
                }
            }
        }
        .task { await load() }
        .onDisappear { player.stop() }
        .sheet(item: $exportItem) { export in
            DocumentExporter(url: export.url) { exportItem = nil }
        }
        .alert("Error", isPresented: Binding(get: { localError != nil },
                                             set: { if !$0 { localError = nil } })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(localError ?? "")
        }
    }

    @ViewBuilder
    private func content(for info: ObjectDataInfo) -> some View {
        switch info.kind {
        case "image":
            VStack(spacing: 0) {
                if let image {
                    ScrollView([.horizontal, .vertical]) {
                        Image(uiImage: image)
                            .resizable()
                            .scaledToFit()
                            .frame(maxWidth: .infinity)
                            .padding()
                    }
                    Text("\(Int(image.size.width * image.scale)) × \(Int(image.size.height * image.scale)) px")
                        .font(.caption).foregroundStyle(.secondary).padding(.top, 4)
                }
                Button {
                    ImportPicker.pick(for: item) { url in
                        guard let url else { return }
                        Task {
                            await vm.importObject(item, from: url)
                            await load()
                        }
                    }
                } label: {
                    Label("Replace image… (Photos / Files)", systemImage: "photo.badge.plus")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .padding()
            }
        case "audio":
            audioContent(info)
        case "mesh":
            VStack(spacing: 6) {
                if let meshURL {
                    MeshPreview(url: meshURL)
                }
                Text("Drag to rotate · pinch to zoom. Use the export button to save the OBJ.")
                    .font(.caption).foregroundStyle(.secondary).padding(.bottom, 8)
            }
        default:
            if let readOnlyReason {
                VStack(spacing: 10) {
                    Image(systemName: "doc.text").font(.largeTitle).foregroundStyle(.secondary)
                    Text(readOnlyReason).font(.footnote).multilineTextAlignment(.center)
                        .foregroundStyle(.secondary)
                }
                .padding()
            } else {
                TextEditor(text: $text)
                    .font(.system(.footnote, design: .monospaced))
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                    .padding(.horizontal, 8)
            }
        }
    }

    @ViewBuilder
    private func audioContent(_ info: ObjectDataInfo) -> some View {
        ScrollView {
            VStack(spacing: 14) {
                Image(systemName: "waveform")
                    .font(.system(size: 52))
                    .foregroundStyle(.secondary)
                    .padding(.top, 24)
                Text(audioSummary(info)).font(.subheadline)
                if let note = info.note, !note.isEmpty {
                    Text(note)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }

                GroupBox("Current audio") {
                    VStack(spacing: 10) {
                        if let audioURL {
                            playButton(audioURL, idle: "Play")
                            Button {
                                Task {
                                    if let url = await vm.convertToM4A(audioURL) { exportItem = ExportItem(url: url) }
                                }
                            } label: {
                                Label("Export as M4A (AAC)", systemImage: "music.note")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.bordered)
                        } else {
                            Text("Preview is not available for this format.")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .frame(maxWidth: .infinity)
                }

                if let pendingWAV {
                    GroupBox("New audio (not applied yet)") {
                        VStack(spacing: 10) {
                            playButton(pendingWAV, idle: "Play new audio")
                            Button {
                                player.stop()
                                Task {
                                    if await vm.applyAudio(item, wav: pendingWAV) {
                                        self.pendingWAV = nil
                                        await load()
                                    }
                                }
                            } label: {
                                Label("Apply replacement", systemImage: "checkmark.circle.fill")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.borderedProminent)
                            Button(role: .destructive) {
                                player.stop()
                                self.pendingWAV = nil
                            } label: {
                                Label("Discard", systemImage: "xmark.circle")
                                    .frame(maxWidth: .infinity)
                            }
                            .buttonStyle(.bordered)
                        }
                        .frame(maxWidth: .infinity)
                    }
                } else {
                    Button {
                        player.stop()
                        ImportPicker.pick(for: item) { url in
                            guard let url else { return }
                            Task {
                                if let wav = await vm.prepareAudio(from: url) { pendingWAV = wav }
                            }
                        }
                    } label: {
                        Label("Replace with audio…", systemImage: "arrow.triangle.2.circlepath")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                }

                Text("Pick an audio file (MP3, M4A, WAV…) or a video (MP4/MOV). Listen to it first, then apply. The new audio is stored as uncompressed PCM, so the bundle grows.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding()
        }
    }

    private func playButton(_ url: URL, idle: String) -> some View {
        Button {
            player.toggle(url)
        } label: {
            Label(player.isPlaying(url) ? "Stop" : idle,
                  systemImage: player.isPlaying(url) ? "stop.fill" : "play.fill")
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.bordered)
    }

    private func audioSummary(_ info: ObjectDataInfo) -> String {
        var parts: [String] = []
        if let f = info.format { parts.append(f) }
        if let c = info.channels, c > 0 { parts.append("\(c) ch") }
        if let hz = info.frequency, hz > 0 { parts.append("\(hz) Hz") }
        if let len = info.length, len > 0 { parts.append(String(format: "%.1f s", len)) }
        parts.append(formatBytes(Int64(info.bytes)))
        return parts.joined(separator: " · ")
    }

    private func isTextual(_ info: ObjectDataInfo) -> Bool {
        info.kind == "text" || info.kind == "json"
    }

    private func load() async {
        loading = true
        loadError = nil
        guard let sid = vm.sessionId else {
            loadError = "Session is empty"
            loading = false
            return
        }
        let dir = makeTempDir("UABEEdit")
        let out = dir.appendingPathComponent("data.bin")
        do {
            let previewFile = dir.appendingPathComponent("preview.wav")
            let result: ObjectDataInfo = try await Backend.shared.call(
                "get_object_data",
                ["sessionId": sid, "idx": item.index, "outPath": out.path, "previewPath": previewFile.path])
            info = result
            switch result.kind {
            case "image":
                image = UIImage(contentsOfFile: out.path)
                if image == nil { loadError = "The texture could not be decoded." }
            case "audio":
                let dest = dir.appendingPathComponent("audio.\(result.ext ?? "bin")")
                try FileManager.default.moveItem(at: out, to: dest)
                if result.preview == true, FileManager.default.fileExists(atPath: previewFile.path) {
                    audioURL = previewFile
                } else if result.playable == true {
                    audioURL = dest
                } else {
                    audioURL = nil
                }
            case "mesh":
                let obj = dir.appendingPathComponent("mesh.obj")
                try FileManager.default.moveItem(at: out, to: obj)
                meshURL = obj
            default:
                readOnlyReason = nil
                if result.bytes > 2_000_000 {
                    readOnlyReason = "This object is too large to edit here (\(formatBytes(Int64(result.bytes)))).\nUse Export / Import instead."
                } else if let s = String(data: try Data(contentsOf: out), encoding: .utf8) {
                    text = s
                } else {
                    readOnlyReason = "This object contains binary data.\nUse Export / Import instead."
                }
            }
        } catch {
            loadError = error.localizedDescription
        }
        loading = false
    }

    private func save(_ info: ObjectDataInfo) async {
        guard let sid = vm.sessionId else { return }
        if info.kind == "json" {
            let parsed = text.data(using: .utf8).flatMap { try? JSONSerialization.jsonObject(with: $0) }
            guard parsed is [String: Any] else {
                localError = "Invalid JSON. Must be a JSON object (starts with { … })."
                return
            }
        }
        saving = true
        defer { saving = false }
        do {
            let file = makeTempDir("UABEEdit").appendingPathComponent("edit.txt")
            try Data(text.utf8).write(to: file)
            let _: Empty = try await Backend.shared.call(
                "import_object", ["sessionId": sid, "idx": item.index, "inPath": file.path])
            vm.markModified(item.index)
            vm.showToast("Saved")
            dismiss()
        } catch {
            localError = "Save failed:\n\(error.localizedDescription)"
        }
    }
}
