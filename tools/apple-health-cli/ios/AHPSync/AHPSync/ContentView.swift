import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var model: SyncViewModel

    var body: some View {
        NavigationStack {
            Form {
                Section("Mac 接收端") {
                    TextField("服务器 URL", text: $model.serverURL)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                        .autocorrectionDisabled()
                    SecureField("Token (AHP_INGEST_TOKEN)", text: $model.token)
                    Stepper("同步最近 \(model.syncDays) 天", value: $model.syncDays, in: 1...90)
                    Toggle("后台定时同步", isOn: $model.backgroundSync)
                }

                Section {
                    Button("请求健康数据权限") {
                        Task { await model.authorize() }
                    }
                    .disabled(model.isBusy)

                    Button("立即同步到 Mac") {
                        Task { await model.syncNow() }
                    }
                    .disabled(model.isBusy)
                }

                Section("状态") {
                    if model.isBusy {
                        ProgressView()
                    }
                    Text(model.status)
                        .font(.footnote)
                        .textSelection(.enabled)
                    if let last = SettingsStore.lastSyncAt {
                        Text("上次：\(last)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Section {
                    Text("免费开源，替代 Health Auto Export。数据格式兼容 ahp serve /api/ingest。")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("AHPSync")
            .onDisappear { model.saveSettings() }
        }
    }
}
