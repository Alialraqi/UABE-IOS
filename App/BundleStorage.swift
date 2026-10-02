import Foundation

final class BundleStorage {
    static let shared = BundleStorage()

    private let defaults = UserDefaults.standard
    private let recentsKey = "recents_json"
    private let lastKey = "last_file"
    private let maxRecents = 15
    let root: URL

    init() {
        let base = (try? FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                                 appropriateFor: nil, create: true))
            ?? FileManager.default.temporaryDirectory
        root = base.appendingPathComponent("Bundles", isDirectory: true)
        try? FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    }

    func url(for recent: RecentBundle) -> URL {
        root.appendingPathComponent(recent.file)
    }

    var recents: [RecentBundle] {
        get {
            guard let data = defaults.data(forKey: recentsKey),
                  let list = try? JSONDecoder().decode([RecentBundle].self, from: data) else { return [] }
            return list.filter { FileManager.default.fileExists(atPath: url(for: $0).path) }
        }
        set {
            defaults.set(try? JSONEncoder().encode(Array(newValue.prefix(maxRecents))), forKey: recentsKey)
        }
    }

    var last: RecentBundle? {
        guard let file = defaults.string(forKey: lastKey) else { return nil }
        return recents.first { $0.file == file }
    }

    func setLast(_ recent: RecentBundle?) {
        defaults.set(recent?.file, forKey: lastKey)
    }

    func importFile(from source: URL) throws -> RecentBundle {
        let folder = UUID().uuidString
        let dir = root.appendingPathComponent(folder, isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let dest = dir.appendingPathComponent(source.lastPathComponent)
        try FileManager.default.copyItem(at: source, to: dest)
        let recent = RecentBundle(name: source.lastPathComponent,
                                  file: "\(folder)/\(source.lastPathComponent)", date: Date())
        var list = recents
        list.insert(recent, at: 0)
        recents = trimmed(list)
        return recent
    }

    func touch(_ recent: RecentBundle) {
        var list = recents.filter { $0.file != recent.file }
        var r = recent
        r.date = Date()
        list.insert(r, at: 0)
        recents = list
    }

    func remove(_ recent: RecentBundle) {
        try? FileManager.default.removeItem(at: url(for: recent).deletingLastPathComponent())
        recents = recents.filter { $0.file != recent.file }
        if defaults.string(forKey: lastKey) == recent.file { setLast(nil) }
    }

    func removeAll() {
        for r in recents { remove(r) }
    }

    private func trimmed(_ list: [RecentBundle]) -> [RecentBundle] {
        guard list.count > maxRecents else { return list }
        for extra in list.dropFirst(maxRecents) {
            try? FileManager.default.removeItem(at: url(for: extra).deletingLastPathComponent())
        }
        return Array(list.prefix(maxRecents))
    }
}

func makeTempDir(_ name: String) -> URL {
    let dir = FileManager.default.temporaryDirectory
        .appendingPathComponent(name, isDirectory: true)
        .appendingPathComponent(UUID().uuidString, isDirectory: true)
    try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    return dir
}
