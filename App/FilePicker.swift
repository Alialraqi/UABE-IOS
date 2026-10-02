import SwiftUI
import UIKit
import UniformTypeIdentifiers

final class FilePicker: NSObject, UIDocumentPickerDelegate {
    private static var current: FilePicker?
    private let completion: (URL?) -> Void

    private init(completion: @escaping (URL?) -> Void) {
        self.completion = completion
    }

    static func pick(types: [UTType], completion: @escaping (URL?) -> Void) {
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: types, asCopy: true)
        picker.allowsMultipleSelection = false
        let helper = FilePicker(completion: completion)
        picker.delegate = helper
        current = helper
        guard let top = topViewController() else {
            current = nil
            completion(nil)
            return
        }
        top.present(picker, animated: true)
    }

    func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
        controller.dismiss(animated: true)
        finish(urls.first)
    }

    func documentPickerWasCancelled(_ controller: UIDocumentPickerViewController) {
        controller.dismiss(animated: true)
        finish(nil)
    }

    private func finish(_ url: URL?) {
        FilePicker.current = nil
        completion(url)
    }

    static func topViewController() -> UIViewController? {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        let scene = scenes.first { $0.activationState == .foregroundActive } ?? scenes.first
        var vc = scene?.windows.first(where: { $0.isKeyWindow })?.rootViewController
            ?? scene?.windows.first?.rootViewController
        while let presented = vc?.presentedViewController { vc = presented }
        return vc
    }
}
