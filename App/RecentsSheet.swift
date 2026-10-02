import SwiftUI

struct RecentsSheet: View {
    @EnvironmentObject var vm: BundleViewModel
    @Environment(\.dismiss) private var dismiss
    var onBrowse: () -> Void

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Button {
                        onBrowse()
                    } label: {
                        Label("Browse…", systemImage: "folder")
                    }
                }
                Section("Recents") {
                    if vm.recents.isEmpty {
                        Text("No recents.").foregroundStyle(.secondary)
                    }
                    ForEach(vm.recents) { recent in
                        Button {
                            dismiss()
                            Task { await vm.open(recent: recent) }
                        } label: {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(recent.name).foregroundColor(.primary).lineLimit(1)
                                Text(recent.date.formatted(date: .abbreviated, time: .shortened))
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                    .onDelete { offsets in
                        for i in offsets { vm.removeRecent(vm.recents[i]) }
                    }
                }
            }
            .navigationTitle("Open bundle")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .primaryAction) {
                    if !vm.recents.isEmpty {
                        Button("Clear all", role: .destructive) { vm.clearRecents() }
                    }
                }
            }
        }
    }
}
