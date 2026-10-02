import SwiftUI
import UniformTypeIdentifiers

private enum ImporterKind {
    case bundle
    case object(ObjectItem)
}

struct ContentView: View {
    @EnvironmentObject var vm: BundleViewModel

    @State private var showSettings = false
    @State private var showRecents = false
    @State private var showFilter = false
    @State private var showDiagnostics = false
    @State private var showKeyAlert = false
    @State private var showCloseConfirm = false
    @State private var keyText = ""
    @State private var editItem: ObjectItem?
    @State private var exportItem: ExportItem?

    var body: some View {
        NavigationStack {
            Group {
                if vm.displayName == nil {
                    emptyState
                } else {
                    objectList
                }
            }
            .navigationTitle(vm.displayName ?? "UABE")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button { showRecents = true } label: { Image(systemName: "folder") }
                }
                ToolbarItem(placement: .navigationBarTrailing) { mainMenu }
            }
        }
        .overlay { if vm.isLoading { loadingCard } }
        .overlay(alignment: .bottom) { toastView }
        .animation(.default, value: vm.toast)
        .task { await vm.autoReopenLast() }
        .sheet(isPresented: $showRecents) {
            RecentsSheet(onBrowse: {
                showRecents = false
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { present(.bundle) }
            })
            .environmentObject(vm)
        }
        .sheet(isPresented: $showFilter) { FilterSheet().environmentObject(vm) }
        .sheet(isPresented: $showDiagnostics) { DiagnosticsView() }
        .sheet(item: $editItem) { EditObjectView(item: $0).environmentObject(vm) }
        .sheet(item: $exportItem) { export in
            DocumentExporter(url: export.url) { exportItem = nil }
        }
        .sheet(isPresented: $showSettings) { SettingsView() }
        .alert("Error", isPresented: Binding(get: { vm.errorMessage != nil },
                                             set: { if !$0 { vm.errorMessage = nil } })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(vm.errorMessage ?? "")
        }
        .alert("Decryption Key", isPresented: $showKeyAlert) {
            TextField("Key", text: $keyText)
            Button("Save") { Task { await vm.setDecryptionKey(keyText) } }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Used for AssetBundles encrypted by the Chinese Unity build. Reload the bundle after changing it.")
        }
        .alert("Close viewer?", isPresented: $showCloseConfirm) {
            Button("Close", role: .destructive) { vm.closeBundle() }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will close the current bundle view.\n\nThe file stays in Recents so you can reopen it later.")
        }
    }

    private var emptyState: some View {
        VStack(spacing: 14) {
            Image(systemName: "shippingbox")
                .font(.system(size: 54))
                .foregroundStyle(.secondary)
            Text("Open a bundle to begin.").font(.headline)
            Text("Supports .unity3d, .bundle and .ab files.\nTip: long-press an item for actions (export/import).")
                .font(.footnote)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button {
                showRecents = true
            } label: {
                Label("Open bundle", systemImage: "folder")
                    .padding(.horizontal, 12)
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
    }

    private var objectList: some View {
        List {
            ForEach(vm.visibleItems) { item in
                Button {
                    editItem = item
                } label: {
                    ObjectRow(item: item)
                }
                .buttonStyle(.plain)
                .contextMenu { contextActions(for: item) }
            }
        }
        .listStyle(.plain)
        .searchable(text: $vm.filter.query,
                    placement: .navigationBarDrawer(displayMode: .always),
                    prompt: "Search name, type, id")
        .safeAreaInset(edge: .top, spacing: 0) { chipsBar }
        .refreshable { await vm.reload() }
    }

    private var chipsBar: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Button { showFilter = true } label: {
                    Label(vm.filter.activeCount > 0 ? "Filter (\(vm.filter.activeCount))" : "Filter",
                          systemImage: "line.3.horizontal.decrease.circle")
                }
                .buttonStyle(.bordered)
                Menu {
                    sortPicker
                } label: {
                    Label("Sort: \(vm.sortMode.rawValue)", systemImage: "arrow.up.arrow.down")
                }
                .buttonStyle(.bordered)
                Spacer()
                Text("\(vm.visibleItems.count)/\(vm.items.count)")
                    .font(.caption).foregroundStyle(.secondary)
            }
            if let status = vm.statusText, !vm.isLoading {
                Text(status).font(.caption2).foregroundStyle(.secondary).lineLimit(2)
            }
        }
        .font(.subheadline)
        .padding(.horizontal)
        .padding(.vertical, 6)
        .background(.bar)
    }

    private var sortPicker: some View {
        Picker("Sort", selection: $vm.sortMode) {
            ForEach(SortMode.allCases) { mode in
                Text(mode.rawValue).tag(mode)
            }
        }
    }

    private var mainMenu: some View {
        Menu {
            Button { present(.bundle) } label: { Label("Open from Files…", systemImage: "folder.badge.plus") }
            Divider()
            Button {
                Task { await vm.reload() }
            } label: { Label("Reload", systemImage: "arrow.clockwise") }
            .disabled(!vm.hasOpenBundle)
            Button {
                Task { if let url = await vm.exportBundleCopy() { exportItem = ExportItem(url: url) } }
            } label: { Label("Export (Save As…)", systemImage: "square.and.arrow.up") }
            .disabled(!vm.hasOpenBundle)
            Button {
                keyText = vm.storedKey
                showKeyAlert = true
            } label: { Label("Decryption Key", systemImage: "key") }
            Divider()
            Button { showSettings = true } label: { Label("Settings", systemImage: "gearshape") }
            Button { showDiagnostics = true } label: { Label("Diagnostics", systemImage: "stethoscope") }
            Button(role: .destructive) {
                showCloseConfirm = true
            } label: { Label("Close", systemImage: "xmark.circle") }
            .disabled(vm.displayName == nil)
        } label: {
            Image(systemName: "ellipsis.circle")
        }
    }

    @ViewBuilder
    private func contextActions(for item: ObjectItem) -> some View {
        Button { editItem = item } label: { Label("Edit / Preview", systemImage: "pencil") }
        Button {
            Task { if let url = await vm.exportObject(item) { exportItem = ExportItem(url: url) } }
        } label: { Label("Export…", systemImage: "square.and.arrow.up") }
        if item.type != "Mesh" {
            Button { present(.object(item)) } label: { Label("Import…", systemImage: "square.and.arrow.down") }
        }
    }

    private var loadingCard: some View {
        VStack(spacing: 10) {
            ProgressView()
            Text(vm.statusText ?? "Working…").font(.footnote)
        }
        .padding(20)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    @ViewBuilder
    private var toastView: some View {
        if let toast = vm.toast {
            Text(toast)
                .font(.footnote.weight(.medium))
                .padding(.horizontal, 14)
                .padding(.vertical, 9)
                .background(.thinMaterial, in: Capsule())
                .padding(.bottom, 24)
                .transition(.opacity)
        }
    }

    private func present(_ kind: ImporterKind) {
        switch kind {
        case .bundle:
            FilePicker.pick(types: [.item]) { url in
                guard let url else { return }
                Task { await vm.openExternal(url) }
            }
        case .object(let item):
            ImportPicker.pick(for: item) { url in
                guard let url else { return }
                Task { await vm.importObject(item, from: url) }
            }
        }
    }
}
