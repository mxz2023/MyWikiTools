import Foundation

enum SettingsStore {
    private enum Key {
        static let serverURL = "ahp.serverURL"
        static let token = "ahp.token"
        static let syncDays = "ahp.syncDays"
        static let backgroundSync = "ahp.backgroundSync"
        static let lastSyncAt = "ahp.lastSyncAt"
        static let lastStatus = "ahp.lastStatus"
    }

    static var serverURL: String {
        get { UserDefaults.standard.string(forKey: Key.serverURL) ?? "http://192.168.1.100:8765/api/ingest" }
        set { UserDefaults.standard.set(newValue, forKey: Key.serverURL) }
    }

    static var token: String {
        get { UserDefaults.standard.string(forKey: Key.token) ?? "" }
        set { UserDefaults.standard.set(newValue, forKey: Key.token) }
    }

    static var syncDays: Int {
        get {
            let v = UserDefaults.standard.integer(forKey: Key.syncDays)
            return v > 0 ? v : 7
        }
        set { UserDefaults.standard.set(newValue, forKey: Key.syncDays) }
    }

    static var backgroundSync: Bool {
        get { UserDefaults.standard.bool(forKey: Key.backgroundSync) }
        set { UserDefaults.standard.set(newValue, forKey: Key.backgroundSync) }
    }

    static var lastSyncAt: String? {
        get { UserDefaults.standard.string(forKey: Key.lastSyncAt) }
        set { UserDefaults.standard.set(newValue, forKey: Key.lastSyncAt) }
    }

    static var lastStatus: String {
        get { UserDefaults.standard.string(forKey: Key.lastStatus) ?? "尚未同步" }
        set { UserDefaults.standard.set(newValue, forKey: Key.lastStatus) }
    }
}
