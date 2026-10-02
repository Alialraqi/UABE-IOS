import Foundation

struct ObjectItem: Identifiable, Hashable, Decodable {
    let index: Int
    let type: String
    let pathId: Int64
    let bytes: Int64?
    let name: String
    let container: String?
    var isModified: Bool = false

    var id: Int { index }

    enum CodingKeys: String, CodingKey {
        case index, type, bytes, name, container
        case pathId = "id"
    }
}

struct OpenBundleResult: Decodable {
    let sessionId: String
    let archives: [String]
    let objects: [ObjectItem]
    let types: [String]
}

struct ObjectInfo: Decodable {
    let type: String
    let filename: String
    let ext: String
    let mime: String
}

struct ObjectDataInfo: Decodable {
    let idx: Int
    let type: String
    let id: Int64
    let name: String
    let kind: String
    let bytes: Int

    let ext: String?
    let channels: Int?
    let frequency: Int?
    let length: Double?
    let format: String?
    let note: String?
    let playable: Bool?
    let preview: Bool?
}

enum SortMode: String, CaseIterable, Identifiable {
    case idx = "Index"
    case name = "Name"
    case type = "Type"
    case size = "Size"
    case edited = "Modified"
    var id: String { rawValue }
}

struct FilterState: Equatable {
    var query: String = ""
    var types: Set<String> = []
    var editedOnly = false
    var minBytes: Int64? = nil
    var maxBytes: Int64? = nil

    var activeCount: Int {
        var n = 0
        if !types.isEmpty { n += 1 }
        if editedOnly { n += 1 }
        if minBytes != nil || maxBytes != nil { n += 1 }
        return n
    }
}

struct RecentBundle: Codable, Identifiable, Equatable {
    var name: String
    var file: String
    var date: Date
    var id: String { file }
}

struct ExportItem: Identifiable {
    let id = UUID()
    let url: URL
}

func formatBytes(_ n: Int64) -> String {
    ByteCountFormatter.string(fromByteCount: n, countStyle: .file)
}
