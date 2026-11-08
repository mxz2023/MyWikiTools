import Foundation
import HealthKit

struct HealthFetchResult {
    var metrics: [[String: Any]]
    var workouts: [[String: Any]]
}

enum HealthKitClientError: LocalizedError {
    case unavailable
    case unauthorized

    var errorDescription: String? {
        switch self {
        case .unavailable: return "此设备不支持 HealthKit"
        case .unauthorized: return "未获得健康数据读取权限"
        }
    }
}

final class HealthKitClient {
    private let store = HKHealthStore()

    func requestAuthorization() async throws {
        guard HKHealthStore.isHealthDataAvailable() else {
            throw HealthKitClientError.unavailable
        }
        let types = readTypes()
        try await store.requestAuthorization(toShare: [], read: types)
    }

    func fetch(days: Int) async throws -> HealthFetchResult {
        guard HKHealthStore.isHealthDataAvailable() else {
            throw HealthKitClientError.unavailable
        }
        let end = Date()
        let start = Calendar.current.date(byAdding: .day, value: -days, to: end) ?? end.addingTimeInterval(-86400 * Double(days))

        async let steps = dailyStepMetrics(start: start, end: end)
        async let heart = heartRateMetrics(start: start, end: end)
        async let sleep = sleepMetrics(start: start, end: end)
        async let energy = quantityMetrics(
            id: .activeEnergyBurned,
            name: "active_energy",
            unit: HKUnit.kilocalorie(),
            haeUnit: "kcal",
            start: start,
            end: end
        )
        async let distance = quantityMetrics(
            id: .distanceWalkingRunning,
            name: "walking_running_distance",
            unit: HKUnit.meter(),
            haeUnit: "m",
            start: start,
            end: end
        )
        async let workouts = workoutPayload(start: start, end: end)

        var metrics: [[String: Any]] = []
        metrics.append(contentsOf: try await steps)
        metrics.append(contentsOf: try await heart)
        metrics.append(contentsOf: try await sleep)
        if let m = try await energy { metrics.append(m) }
        if let m = try await distance { metrics.append(m) }

        return HealthFetchResult(metrics: metrics, workouts: try await workouts)
    }

    private func readTypes() -> Set<HKObjectType> {
        var set = Set<HKObjectType>()
        let qids: [HKQuantityTypeIdentifier] = [
            .stepCount, .heartRate, .restingHeartRate,
            .activeEnergyBurned, .distanceWalkingRunning,
        ]
        for id in qids {
            if let t = HKObjectType.quantityType(forIdentifier: id) {
                set.insert(t)
            }
        }
        if let sleep = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) {
            set.insert(sleep)
        }
        set.insert(HKObjectType.workoutType())
        return set
    }

    private func dailyStepMetrics(start: Date, end: Date) async throws -> [[String: Any]] {
        guard let qtype = HKObjectType.quantityType(forIdentifier: .stepCount) else { return [] }
        let interval = DateComponents(day: 1)
        let points = try await statisticsCollection(
            type: qtype,
            unit: .count(),
            start: start,
            end: end,
            interval: interval
        ) { date, value in
            [
                "date": HAEFormat.localDate(date),
                "qty": value,
                "source": "AHPSync",
            ]
        }
        guard !points.isEmpty else { return [] }
        return [["name": "step_count", "units": "count", "data": points]]
    }

    private func heartRateMetrics(start: Date, end: Date) async throws -> [[String: Any]] {
        guard let qtype = HKObjectType.quantityType(forIdentifier: .heartRate) else { return [] }
        let samples = try await sampleQuery(type: qtype, start: start, end: end)
        let unit = HKUnit.count().unitDivided(by: .minute())
        var points: [[String: Any]] = []
        for s in samples {
            guard let qs = s as? HKQuantitySample else { continue }
            let bpm = qs.quantity.doubleValue(for: unit)
            points.append([
                "date": HAEFormat.localDate(qs.startDate),
                "Avg": bpm,
                "Min": bpm,
                "Max": bpm,
                "source": qs.sourceRevision.source.name,
            ])
        }
        guard !points.isEmpty else { return [] }
        return [["name": "heart_rate", "units": "bpm", "data": points]]
    }

    private func sleepMetrics(start: Date, end: Date) async throws -> [[String: Any]] {
        guard let ctype = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) else { return [] }
        let samples = try await sampleQuery(type: ctype, start: start, end: end)
        var points: [[String: Any]] = []
        for s in samples {
            guard let cs = s as? HKCategorySample else { continue }
            let hours = cs.endDate.timeIntervalSince(cs.startDate) / 3600.0
            points.append([
                "startDate": HAEFormat.localDate(cs.startDate),
                "endDate": HAEFormat.localDate(cs.endDate),
                "qty": hours,
                "value": HAEFormat.sleepLabel(cs.value),
                "source": cs.sourceRevision.source.name,
            ])
        }
        guard !points.isEmpty else { return [] }
        return [["name": "sleep_analysis", "units": "hr", "data": points]]
    }

    private func quantityMetrics(
        id: HKQuantityTypeIdentifier,
        name: String,
        unit: HKUnit,
        haeUnit: String,
        start: Date,
        end: Date
    ) async throws -> [String: Any]? {
        guard let qtype = HKObjectType.quantityType(forIdentifier: id) else { return nil }
        let interval = DateComponents(day: 1)
        let points = try await statisticsCollection(
            type: qtype,
            unit: unit,
            start: start,
            end: end,
            interval: interval
        ) { date, value in
            ["date": HAEFormat.localDate(date), "qty": value, "source": "AHPSync"]
        }
        guard !points.isEmpty else { return nil }
        return ["name": name, "units": haeUnit, "data": points]
    }

    private func workoutPayload(start: Date, end: Date) async throws -> [[String: Any]] {
        let wtype = HKObjectType.workoutType()
        let samples = try await sampleQuery(type: wtype, start: start, end: end)
        return (samples as? [HKWorkout] ?? []).map { w in
            var row: [String: Any] = [
                "id": w.uuid.uuidString,
                "name": HAEFormat.workoutName(w.workoutActivityType),
                "start": HAEFormat.localDate(w.startDate),
                "end": HAEFormat.localDate(w.endDate),
                "duration": w.duration,
            ]
            if let e = w.totalEnergyBurned {
                row["activeEnergyBurned"] = ["qty": e.doubleValue(for: .kilocalorie()), "units": "kcal"]
            }
            if let d = w.totalDistance {
                row["distance"] = ["qty": d.doubleValue(for: .meter()), "units": "m"]
            }
            return row
        }
    }

    private func statisticsCollection(
        type: HKQuantityType,
        unit: HKUnit,
        start: Date,
        end: Date,
        interval: DateComponents,
        map: @escaping (Date, Double) -> [String: Any]
    ) async throws -> [[String: Any]] {
        try await withCheckedThrowingContinuation { cont in
            let predicate = HKQuery.predicateForSamples(withStart: start, end: end)
            let anchor = Calendar.current.startOfDay(for: start)
            let query = HKStatisticsCollectionQuery(
                quantityType: type,
                quantitySamplePredicate: predicate,
                options: .cumulativeSum,
                anchorDate: anchor,
                intervalComponents: interval
            )
            query.initialResultsHandler = { _, collection, error in
                if let error {
                    cont.resume(throwing: error)
                    return
                }
                guard let collection else {
                    cont.resume(returning: [])
                    return
                }
                var points: [[String: Any]] = []
                collection.enumerateStatistics(from: start, to: end) { stats, _ in
                    guard let sum = stats.sumQuantity() else { return }
                    let value = sum.doubleValue(for: unit)
                    if value > 0 {
                        points.append(map(stats.startDate, value))
                    }
                }
                cont.resume(returning: points)
            }
            store.execute(query)
        }
    }

    private func sampleQuery(type: HKSampleType, start: Date, end: Date) async throws -> [HKSample] {
        try await withCheckedThrowingContinuation { cont in
            let predicate = HKQuery.predicateForSamples(withStart: start, end: end)
            let query = HKSampleQuery(
                sampleType: type,
                predicate: predicate,
                limit: HKObjectQueryNoLimit,
                sortDescriptors: [NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: true)]
            ) { _, samples, error in
                if let error {
                    cont.resume(throwing: error)
                    return
                }
                cont.resume(returning: samples ?? [])
            }
            store.execute(query)
        }
    }
}

enum HAEFormat {
    static func localDate(_ date: Date) -> String {
        let fmt = DateFormatter()
        fmt.locale = Locale(identifier: "en_US_POSIX")
        fmt.dateFormat = "yyyy-MM-dd HH:mm:ss ZZZZZ"
        return fmt.string(from: date)
    }

    static func sleepLabel(_ value: Int) -> String {
        switch value {
        case HKCategoryValueSleepAnalysis.inBed.rawValue: return "In Bed"
        case HKCategoryValueSleepAnalysis.awake.rawValue: return "Awake"
        case HKCategoryValueSleepAnalysis.asleepUnspecified.rawValue: return "Asleep"
        case HKCategoryValueSleepAnalysis.asleepCore.rawValue: return "Core"
        case HKCategoryValueSleepAnalysis.asleepDeep.rawValue: return "Deep"
        case HKCategoryValueSleepAnalysis.asleepREM.rawValue: return "REM"
        default: return "Asleep"
        }
    }

    static func workoutName(_ type: HKWorkoutActivityType) -> String {
        switch type {
        case .running: return "Running"
        case .walking: return "Walking"
        case .cycling: return "Cycling"
        case .swimming: return "Swimming"
        case .hiking: return "Hiking"
        case .yoga: return "Yoga"
        default: return "Workout"
        }
    }
}
