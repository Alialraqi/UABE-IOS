import SwiftUI

struct ObjectRow: View {
    let item: ObjectItem

    var body: some View {
        HStack(spacing: 12) {
            TypeBadge(type: item.type)
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(item.name)
                        .font(.body)
                        .lineLimit(1)
                    if item.isModified {
                        Text("Edited")
                            .font(.caption2.weight(.semibold))
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.orange.opacity(0.2), in: Capsule())
                            .foregroundColor(.orange)
                    }
                }
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer(minLength: 0)
            if let bytes = item.bytes {
                Text(formatBytes(bytes))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .contentShape(Rectangle())
    }

    private var subtitle: String {
        var parts = [item.type, "#\(item.index)", "id \(item.pathId)"]
        if let c = item.container, !c.isEmpty { parts.append(c) }
        return parts.joined(separator: " · ")
    }
}

struct TypeBadge: View {
    let type: String

    var body: some View {
        Image(systemName: symbol)
            .font(.system(size: 16, weight: .semibold))
            .foregroundColor(.white)
            .frame(width: 36, height: 36)
            .background(color, in: RoundedRectangle(cornerRadius: 9, style: .continuous))
    }

    private var symbol: String {
        switch type {
        case "Texture2D", "Sprite": return "photo"
        case "Mesh": return "cube"
        case "TextAsset": return "doc.text"
        case "AudioClip": return "waveform"
        case "GameObject", "Transform": return "square.stack.3d.up"
        case "MonoBehaviour", "MonoScript": return "curlybraces"
        case "Material", "Shader": return "paintpalette"
        case "AssetBundle": return "shippingbox"
        default: return "questionmark.square.dashed"
        }
    }

    private var color: Color {
        switch type {
        case "Texture2D", "Sprite": return .blue
        case "Mesh": return .purple
        case "TextAsset": return .green
        case "AudioClip": return .pink
        case "MonoBehaviour", "MonoScript": return .orange
        default: return .gray
        }
    }
}
