import SwiftUI

@main
struct AHPSyncApp: App {
    @StateObject private var sync = SyncViewModel()

    init() {
        BackgroundSync.register()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(sync)
                .onAppear {
                    BackgroundSync.scheduleIfEnabled()
                }
        }
    }
}
