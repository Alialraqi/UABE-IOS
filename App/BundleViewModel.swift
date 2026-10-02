import Foundation
import SwiftUI

@MainActor
final class BundleViewModel: ObservableObject {
    @Published private(set) var items: [ObjectItem] = []
    @Published private(set) var visibleItems: [ObjectItem] = []
    @Published private(set) var allTypes: [String] = []
    @Published private(set) var sessionId: String?
    @Published private(set) var recents: [RecentBundle] = []
    @Published var displayName: String?
    @Published var isLoading = false
    @Published var statusText: String?
    @Published var errorMessage: String?
    @Published var toast: String?

    @Published var sortMode: SortMode = .idx { didSet { publish() } }
    @Published var filter = FilterState() { didSet { publish() } }

    private(set) var currentURL: URL?
    private var modified = Set<Int>()
    private var autosaveTask: Task<Void, Never>?
    private var toastTask: Task<Void, Never>?
    private let storage = BundleStorage.shared

    var hasOpenBundle: Bool { sessionId != nil }

    init() {
        recents = storage.recents
    }

    func autoReopenLast() async {
        guard !hasOpenBundle, let last = storage.last else { return }
        await open(recent: last)
    }

    func openExternal(_ url: URL) async {
        isLoading = true
        statusText = "Copying…"
        let storage = self.storage
        let result: Result<RecentBundle, Error> = await Task.detached { () -> Result<RecentBundle, Error> in
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            do { return .success(try storage.importFile(from: url)) } catch { return .failure(error) }
        }.value
        switch result {
        case .success(let recent):
            recents = storage.recents
            await open(recent: recent)
        case .failure(let error):
            isLoading = false
            statusText = nil
            errorMessage = "Copy failed: \(error.localizedDescription)"
        }
    }

    func open(recent: RecentBundle) async {
        let url = storage.url(for: recent)
        guard FileManager.default.fileExists(atPath: url.path) else {
            errorMessage = "Recent file missing."
            recents = storage.recents
            return
        }
        storage.touch(recent)
        storage.setLast(recent)
        recents = storage.recents
        await openLocal(url, name: recent.name)
    }

    private func openLocal(_ url: URL, name: String) async {
        autosaveTask?.cancel()
        await closeSession()
        currentURL = url
        displayName = name
        modified.removeAll()
        items = []
        publish()
        isLoading = true
        statusText = "Scanning…"
        do {
            applyStoredKey()
            let result: OpenBundleResult = try await Backend.shared.call("open_bundle", ["path": url.path])
            sessionId = result.sessionId
            apply(result)
            statusText = result.archives.isEmpty ? nil : result.archives.joined(separator: ", ")
        } catch {
            statusText = nil
            errorMessage = "Scan failed:\n\(error.localizedDescription)"
        }
        isLoading = false
    }

    private func apply(_ result: OpenBundleResult) {
        var list = result.objects
        for i in list.indices { list[i].isModified = modified.contains(list[i].index) }
        items = list
        allTypes = result.types
        publish()
    }

    private func closeSession() async {
        if let sid = sessionId {
            let _: Empty? = try? await Backend.shared.call("close_bundle", ["sessionId": sid])
        }
        sessionId = nil
    }

    func closeBundle() {
        autosaveTask?.cancel()
        if let sid = sessionId {
            Task { let _: Empty? = try? await Backend.shared.call("close_bundle", ["sessionId": sid]) }
        }
        sessionId = nil
        currentURL = nil
        displayName = nil
        items = []
        allTypes = []
        modified.removeAll()
        filter = FilterState()
        statusText = nil
        publish()
    }

    func reload() async {
        guard let url = currentURL, let name = displayName else { return }
        await openLocal(url, name: name)
    }

    var storedKey: String {
        get { UserDefaults.standard.string(forKey: "decrypt_key") ?? "" }
        set { UserDefaults.standard.set(newValue, forKey: "decrypt_key") }
    }

    private func applyStoredKey() {
        let key = storedKey
        guard !key.isEmpty else { return }
        Task { let _: Empty? = try? await Backend.shared.call("set_decrypt_key", ["key": key]) }
    }

    func setDecryptionKey(_ key: String) async {
        storedKey = key
        do {
            let _: Empty = try await Backend.shared.call("set_decrypt_key", ["key": key])
            showToast("Key saved. Reload the bundle to apply it.")
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func exportObject(_ item: ObjectItem) async -> URL? {
        guard let sid = sessionId else { errorMessage = "Session is empty"; return nil }
        isLoading = true
        statusText = "Exporting…"
        defer { isLoading = false; statusText = nil }
        do {
            let info: ObjectInfo = try await Backend.shared.call("object_info", ["sessionId": sid, "idx": item.index])
            let dir = makeTempDir("UABEExport")
            let out = dir.appendingPathComponent("\(info.filename).\(info.ext)")
            let _: Empty = try await Backend.shared.call(
                "export_object", ["sessionId": sid, "idx": item.index, "outPath": out.path])
            return out
        } catch {
            errorMessage = "Export failed:\n\(error.localizedDescription)"
            return nil
        }
    }

    func importObject(_ item: ObjectItem, from source: URL) async {
        guard let sid = sessionId else { errorMessage = "Session is empty"; return }
        isLoading = true
        statusText = "Importing…"
        defer { isLoading = false; statusText = nil }
        do {
            let local = try copyToTemp(source)
            if item.type == "AudioClip" {
                statusText = "Converting audio…"
                let wav = try await AudioTools.toWAV(local)
                statusText = "Importing…"
                let _: Empty = try await Backend.shared.call(
                    "replace_audio", ["sessionId": sid, "idx": item.index, "inPath": wav.path])
            } else {
                let _: Empty = try await Backend.shared.call(
                    "import_object", ["sessionId": sid, "idx": item.index, "inPath": local.path])
            }
            markModified(item.index)
            showToast("Imported")
        } catch {
            errorMessage = "Import failed:\n\(error.localizedDescription)"
        }
    }

    func convertToM4A(_ source: URL) async -> URL? {
        isLoading = true
        statusText = "Converting to M4A…"
        defer { isLoading = false; statusText = nil }
        do {
            return try await AudioTools.toM4A(source)
        } catch {
            errorMessage = "M4A conversion failed:\n\(error.localizedDescription)"
            return nil
        }
    }

    func prepareAudio(from source: URL) async -> URL? {
        isLoading = true
        statusText = "Converting audio…"
        defer { isLoading = false; statusText = nil }
        do {
            let local = try copyToTemp(source)
            return try await AudioTools.toWAV(local)
        } catch {
            errorMessage = "Audio import failed:\n\(error.localizedDescription)"
            return nil
        }
    }

    func applyAudio(_ item: ObjectItem, wav: URL) async -> Bool {
        guard let sid = sessionId else { errorMessage = "Session is empty"; return false }
        isLoading = true
        statusText = "Replacing audio…"
        defer { isLoading = false; statusText = nil }
        do {
            let _: Empty = try await Backend.shared.call(
                "replace_audio", ["sessionId": sid, "idx": item.index, "inPath": wav.path])
            markModified(item.index)
            showToast("Audio replaced")
            return true
        } catch {
            errorMessage = "Import failed:\n\(error.localizedDescription)"
            return false
        }
    }

    private func copyToTemp(_ source: URL) throws -> URL {
        let scoped = source.startAccessingSecurityScopedResource()
        defer { if scoped { source.stopAccessingSecurityScopedResource() } }
        let dest = makeTempDir("UABEImport").appendingPathComponent(source.lastPathComponent)
        try FileManager.default.copyItem(at: source, to: dest)
        return dest
    }

    func markModified(_ index: Int) {
        modified.insert(index)
        if let i = items.firstIndex(where: { $0.index == index }) { items[i].isModified = true }
        publish()
        autosaveTask?.cancel()
        autosaveTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 700_000_000)
            guard !Task.isCancelled else { return }
            await self?.autosave()
        }
    }

    func autosave() async {
        guard let sid = sessionId, let url = currentURL else { return }
        do {
            let result: SaveResult = try await Backend.shared.call(
                "save_bundle", ["sessionId": sid, "outPath": url.path, "reload": true])
            if let reloaded = result.reloaded { apply(reloaded) }
        } catch {
            errorMessage = "Save failed:\n\(error.localizedDescription)"
        }
    }

    private struct SaveResult: Decodable {
        let bytes: Int
        let reloaded: OpenBundleResult?
    }

    func exportBundleCopy() async -> URL? {
        guard let url = currentURL, let name = displayName else { return nil }
        if autosaveTask != nil { autosaveTask?.cancel(); autosaveTask = nil; await autosave() }
        isLoading = true
        statusText = "Preparing export…"
        defer { isLoading = false; statusText = nil }
        do {
            let dest = makeTempDir("UABEBundle").appendingPathComponent(name)
            try FileManager.default.copyItem(at: url, to: dest)
            return dest
        } catch {
            errorMessage = "Export failed:\n\(error.localizedDescription)"
            return nil
        }
    }

    func removeRecent(_ recent: RecentBundle) {
        storage.remove(recent)
        recents = storage.recents
    }

    func clearRecents() {
        storage.removeAll()
        recents = storage.recents
    }

    private func publish() {
        let f = filter
        let q = f.query.trimmingCharacters(in: .whitespaces).lowercased()
        let allowed = Set(f.types.map { $0.lowercased() })

        let filtered = items.filter { it in
            if f.editedOnly && !it.isModified { return false }
            let size = it.bytes ?? -1
            if let min = f.minBytes, size < 0 || size < min { return false }
            if let max = f.maxBytes, size < 0 || size > max { return false }
            if !allowed.isEmpty && !allowed.contains(it.type.lowercased()) { return false }
            if !q.isEmpty {
                return it.name.lowercased().contains(q) || it.type.lowercased().contains(q)
                    || String(it.index).contains(q) || String(it.pathId).contains(q)
            }
            return true
        }
        visibleItems = filtered.sorted(by: comparator(sortMode))
    }

    private func comparator(_ mode: SortMode) -> (ObjectItem, ObjectItem) -> Bool {
        switch mode {
        case .idx:
            return { $0.index < $1.index }
        case .name:
            return { a, b in
                let r = a.name.caseInsensitiveCompare(b.name)
                return r == .orderedSame ? a.index < b.index : r == .orderedAscending
            }
        case .type:
            return { a, b in
                let r = a.type.caseInsensitiveCompare(b.type)
                return r == .orderedSame ? a.index < b.index : r == .orderedAscending
            }
        case .size:
            return { a, b in
                let x = a.bytes ?? -1, y = b.bytes ?? -1
                return x == y ? a.index < b.index : x > y
            }
        case .edited:
            return { a, b in
                a.isModified == b.isModified ? a.index < b.index : a.isModified
            }
        }
    }

    func showToast(_ text: String) {
        toast = text
        toastTask?.cancel()
        toastTask = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 2_200_000_000)
            guard !Task.isCancelled else { return }
            self?.toast = nil
        }
    }
}
