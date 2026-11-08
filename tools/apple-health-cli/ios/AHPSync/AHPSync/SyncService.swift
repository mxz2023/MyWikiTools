import Foundation

enum SyncService {
    static func buildPayload(_ fetch: HealthFetchResult) -> [String: Any] {
        ["data": ["metrics": fetch.metrics, "workouts": fetch.workouts]]
    }

    static func upload(payload: [String: Any], serverURL: String, token: String) async throws -> String {
        guard let url = URL(string: serverURL.trimmingCharacters(in: .whitespacesAndNewlines)) else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if !token.isEmpty {
            request.setValue(token, forHTTPHeaderField: "api-key")
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        let text = String(data: data, encoding: .utf8) ?? ""
        guard (200..<300).contains(http.statusCode) else {
            throw NSError(domain: "AHPSync", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: "HTTP \(http.statusCode): \(text.prefix(200))"])
        }
        return text
    }
}
