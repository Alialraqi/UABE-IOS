import PhotosUI
import UIKit
import UniformTypeIdentifiers

enum ImportPicker {
    static func pick(for item: ObjectItem, completion: @escaping (URL?) -> Void) {
        switch item.type {
        case "Texture2D":
            chooseImageSource(completion: completion)
        case "AudioClip":
            FilePicker.pick(types: [.audio, .movie, .mpeg4Movie], completion: completion)
        default:
            FilePicker.pick(types: [.item], completion: completion)
        }
    }

    private static func chooseImageSource(completion: @escaping (URL?) -> Void) {
        guard let top = FilePicker.topViewController() else { completion(nil); return }
        let sheet = UIAlertController(title: "Import image", message: nil, preferredStyle: .actionSheet)
        sheet.addAction(UIAlertAction(title: "Photo Library", style: .default) { _ in
            PhotoPicker.pick(completion)
        })
        sheet.addAction(UIAlertAction(title: "Files", style: .default) { _ in
            FilePicker.pick(types: [.image], completion: completion)
        })
        sheet.addAction(UIAlertAction(title: "Cancel", style: .cancel) { _ in completion(nil) })
        if let pop = sheet.popoverPresentationController {
            pop.sourceView = top.view
            pop.sourceRect = CGRect(x: top.view.bounds.midX, y: top.view.bounds.midY, width: 1, height: 1)
            pop.permittedArrowDirections = []
        }
        top.present(sheet, animated: true)
    }
}

final class PhotoPicker: NSObject, PHPickerViewControllerDelegate {
    private static var current: PhotoPicker?
    private let completion: (URL?) -> Void

    private init(completion: @escaping (URL?) -> Void) { self.completion = completion }

    static func pick(_ completion: @escaping (URL?) -> Void) {
        var config = PHPickerConfiguration()
        config.filter = .images
        config.selectionLimit = 1
        let picker = PHPickerViewController(configuration: config)
        let helper = PhotoPicker(completion: completion)
        picker.delegate = helper
        current = helper
        guard let top = FilePicker.topViewController() else {
            current = nil
            completion(nil)
            return
        }
        top.present(picker, animated: true)
    }

    func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
        picker.dismiss(animated: true)
        guard let provider = results.first?.itemProvider,
              provider.canLoadObject(ofClass: UIImage.self) else {
            finish(nil)
            return
        }
        provider.loadObject(ofClass: UIImage.self) { object, _ in
            var url: URL?
            if let image = object as? UIImage, let data = image.pngData() {
                let dest = makeTempDir("UABEPhoto").appendingPathComponent("photo.png")
                if (try? data.write(to: dest)) != nil { url = dest }
            }
            DispatchQueue.main.async { self.finish(url) }
        }
    }

    private func finish(_ url: URL?) {
        PhotoPicker.current = nil
        completion(url)
    }
}
