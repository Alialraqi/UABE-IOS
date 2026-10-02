import SwiftUI

struct FilterSheet: View {
    @EnvironmentObject var vm: BundleViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var minText = ""
    @State private var maxText = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Types") {
                    ForEach(vm.allTypes, id: \.self) { type in
                        Button {
                            toggle(type)
                        } label: {
                            HStack {
                                Text(type).foregroundColor(.primary)
                                Spacer()
                                if vm.filter.types.contains(type) {
                                    Image(systemName: "checkmark").foregroundColor(.accentColor)
                                }
                            }
                        }
                    }
                }
                Section("Modified") {
                    Toggle("Edited only", isOn: Binding(
                        get: { vm.filter.editedOnly },
                        set: { vm.filter.editedOnly = $0 }))
                }
                Section("Size (KB)") {
                    TextField("Minimum", text: $minText).keyboardType(.numberPad)
                    TextField("Maximum", text: $maxText).keyboardType(.numberPad)
                }
                Section {
                    Button("Clear filters", role: .destructive) {
                        vm.filter = FilterState(query: vm.filter.query)
                        minText = ""
                        maxText = ""
                    }
                }
            }
            .navigationTitle("Filter")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") {
                        vm.filter.minBytes = Int64(minText).map { $0 * 1024 }
                        vm.filter.maxBytes = Int64(maxText).map { $0 * 1024 }
                        dismiss()
                    }
                }
            }
            .onAppear {
                minText = vm.filter.minBytes.map { String($0 / 1024) } ?? ""
                maxText = vm.filter.maxBytes.map { String($0 / 1024) } ?? ""
            }
        }
    }

    private func toggle(_ type: String) {
        if vm.filter.types.contains(type) {
            vm.filter.types.remove(type)
        } else {
            vm.filter.types.insert(type)
        }
    }
}
