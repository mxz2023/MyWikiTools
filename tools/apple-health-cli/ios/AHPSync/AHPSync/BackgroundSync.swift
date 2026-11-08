import BackgroundTasks
import UIKit

enum BackgroundSync {
    static let taskId = "com.mywikitools.ahpsync.refresh"

    static func register() {
        BGTaskScheduler.shared.register(forTaskWithIdentifier: taskId, using: nil) { task in
            guard let refresh = task as? BGAppRefreshTask else {
                task.setTaskCompleted(success: false)
                return
            }
            handle(refresh)
        }
    }

    static func scheduleIfEnabled() {
        guard SettingsStore.backgroundSync else { return }
        let request = BGAppRefreshTaskRequest(identifier: taskId)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 4 * 3600)
        try? BGTaskScheduler.shared.submit(request)
    }

    private static func handle(_ task: BGAppRefreshTask) {
        scheduleIfEnabled()
        let work = Task {
            let client = HealthKitClient()
            do {
                let fetch = try await client.fetch(days: SettingsStore.syncDays)
                let payload = SyncService.buildPayload(fetch)
                _ = try await SyncService.upload(
                    payload: payload,
                    serverURL: SettingsStore.serverURL,
                    token: SettingsStore.token
                )
                SettingsStore.lastStatus = "后台同步成功"
                task.setTaskCompleted(success: true)
            } catch {
                SettingsStore.lastStatus = "后台同步失败：\(error.localizedDescription)"
                task.setTaskCompleted(success: false)
            }
        }
        task.expirationHandler = {
            work.cancel()
        }
    }
}
