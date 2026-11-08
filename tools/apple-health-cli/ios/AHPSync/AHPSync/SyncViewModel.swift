import Foundation

@MainActor
final class SyncViewModel: ObservableObject {
    @Published var serverURL: String = SettingsStore.serverURL
    @Published var token: String = SettingsStore.token
    @Published var syncDays: Int = SettingsStore.syncDays
    @Published var backgroundSync: Bool = SettingsStore.backgroundSync
    @Published var status: String = SettingsStore.lastStatus
    @Published var isBusy = false

    private let client = HealthKitClient()

    func saveSettings() {
        SettingsStore.serverURL = serverURL
        SettingsStore.token = token
        SettingsStore.syncDays = syncDays
        SettingsStore.backgroundSync = backgroundSync
        BackgroundSync.scheduleIfEnabled()
    }

    func authorize() async {
        isBusy = true
        defer { isBusy = false }
        do {
            try await client.requestAuthorization()
            status = "已请求健康权限，请在弹窗中允许读取。"
            SettingsStore.lastStatus = status
        } catch {
            status = "授权失败：\(error.localizedDescription)"
            SettingsStore.lastStatus = status
        }
    }

    func syncNow() async {
        saveSettings()
        isBusy = true
        defer { isBusy = false }
        do {
            let fetch = try await client.fetch(days: syncDays)
            let payload = SyncService.buildPayload(fetch)
            let response = try await SyncService.upload(payload: payload, serverURL: serverURL, token: token)
            let iso = ISO8601DateFormatter().string(from: Date())
            SettingsStore.lastSyncAt = iso
            status = "同步成功 \(iso)\n\(response.prefix(120))"
            SettingsStore.lastStatus = status
        } catch {
            status = "同步失败：\(error.localizedDescription)"
            SettingsStore.lastStatus = status
        }
    }
}
