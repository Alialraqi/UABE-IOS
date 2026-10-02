import SwiftUI

struct DiagnosticsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var rows: [(String, String)] = []
    @State private var error: String?

    var body: some View {
        NavigationStack {
            List {
                if let error {
                    Text(error).font(.footnote).foregroundColor(.red)
                }
                ForEach(rows, id: \.0) { row in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(row.0).font(.subheadline)
                        Text(row.1)
                            .font(.caption)
                            .foregroundColor(row.1.hasPrefix("MISSING") ? .red : .secondary)
                    }
                }
            }
            .navigationTitle("Diagnostics")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } }
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        UIPasteboard.general.string = rows.map { "\($0.0): \($0.1)" }.joined(separator: "\n")
                    } label: { Image(systemName: "doc.on.doc") }
                }
            }
            .task {
                do {
                    let info: [String: String] = try await Backend.shared.call("ping")
                    rows = info.sorted { $0.key < $1.key }.map { ($0.key, $0.value) }
                } catch {
                    self.error = error.localizedDescription
                }
            }
        }
    }
}
