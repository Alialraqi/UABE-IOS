import Foundation

struct BackendError: LocalizedError {
    let message: String
    let trace: String?
    var errorDescription: String? { message }
}

struct Empty: Decodable {}

private struct Envelope<T: Decodable>: Decodable {
    let ok: Bool
    let data: T?
    let error: String?
    let trace: String?
}

final class PythonWorker {
    private var thread: Thread!
    private let cond = NSCondition()
    private var jobs: [() -> Void] = []

    init(stackSize: Int = 64 * 1024 * 1024) {
        thread = Thread { [unowned self] in self.loop() }
        thread.name = "uabe.python"
        thread.stackSize = stackSize
        thread.qualityOfService = .userInitiated
        thread.start()
    }

    private func loop() {
        while true {
            cond.lock()
            while jobs.isEmpty { cond.wait() }
            let job = jobs.removeFirst()
            cond.unlock()
            job()
        }
    }

    func run<T>(_ work: @escaping () throws -> T) async throws -> T {
        try await withCheckedThrowingContinuation { (cont: CheckedContinuation<T, Error>) in
            cond.lock()
            jobs.append {
                do { cont.resume(returning: try work()) } catch { cont.resume(throwing: error) }
            }
            cond.signal()
            cond.unlock()
        }
    }
}

final class Backend {
    static let shared = Backend()

    private let worker = PythonWorker()
    private var started = false
    private var startError: String?

    func call<T: Decodable>(_ method: String, _ payload: [String: Any] = [:]) async throws -> T {
        let body = try JSONSerialization.data(withJSONObject: payload)
        let json = String(data: body, encoding: .utf8) ?? "{}"
        let raw: String = try await worker.run { [self] in
            if !started {
                startError = PythonRuntime.start()
                started = true
            }
            if let err = startError {
                throw BackendError(message: "Python failed to start:\n\(err)", trace: nil)
            }
            return PythonRuntime.callMethod(method, payload: json)
        }
        guard let bytes = raw.data(using: .utf8) else {
            throw BackendError(message: "Bad reply encoding", trace: nil)
        }
        let envelope = try JSONDecoder().decode(Envelope<T>.self, from: bytes)
        if envelope.ok, let value = envelope.data { return value }
        throw BackendError(message: envelope.error ?? "Unknown error", trace: envelope.trace)
    }
}
