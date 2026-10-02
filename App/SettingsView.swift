import SwiftUI

enum AppearanceMode: String, CaseIterable, Identifiable {
    case system, light, dark
    var id: String { rawValue }

    var title: String {
        switch self {
        case .system: return "System"
        case .light: return "Light"
        case .dark: return "Dark"
        }
    }

    var colorScheme: ColorScheme? {
        switch self {
        case .system: return nil
        case .light: return .light
        case .dark: return .dark
        }
    }
}

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @AppStorage("appearance") private var appearance = AppearanceMode.system.rawValue

    var body: some View {
        NavigationStack {
            Form {
                Section("Appearance") {
                    Picker("Theme", selection: $appearance) {
                        ForEach(AppearanceMode.allCases) { mode in
                            Text(mode.title).tag(mode.rawValue)
                        }
                    }
                    .pickerStyle(.segmented)
                }
                Section("Developer") {
                    Link(destination: URL(string: "https://www.tiktok.com/@frezcode")!) {
                        HStack(spacing: 12) {
                            TikTokBadge()
                            VStack(alignment: .leading, spacing: 2) {
                                Text("TikTok").foregroundColor(.primary)
                                Text("@frezcode").font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Image(systemName: "arrow.up.right")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } }
            }
        }
    }
}

struct TikTokBadge: View {
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 9, style: .continuous).fill(Color.black)
            Image(systemName: "music.note")
                .font(.system(size: 17, weight: .bold))
                .foregroundColor(Color(red: 0.15, green: 0.95, blue: 0.93))
                .offset(x: -1.2, y: -1)
            Image(systemName: "music.note")
                .font(.system(size: 17, weight: .bold))
                .foregroundColor(Color(red: 1.0, green: 0.16, blue: 0.33))
                .offset(x: 1.2, y: 1)
            Image(systemName: "music.note")
                .font(.system(size: 17, weight: .bold))
                .foregroundColor(.white)
        }
        .frame(width: 36, height: 36)
    }
}
