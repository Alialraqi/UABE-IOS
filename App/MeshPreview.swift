import SwiftUI
import SceneKit
import SceneKit.ModelIO
import ModelIO

struct MeshPreview: UIViewRepresentable {
    let url: URL

    func makeUIView(context: Context) -> SCNView {
        let view = SCNView()
        view.backgroundColor = .clear
        view.allowsCameraControl = true
        view.autoenablesDefaultLighting = true
        view.antialiasingMode = .multisampling4X
        view.scene = MeshPreview.makeScene(url: url, view: view)
        return view
    }

    func updateUIView(_ view: SCNView, context: Context) {}

    private static func makeScene(url: URL, view: SCNView) -> SCNScene {
        let asset = MDLAsset(url: url)
        let scene = SCNScene(mdlAsset: asset)

        let material = SCNMaterial()
        material.diffuse.contents = UIColor(white: 0.82, alpha: 1)
        material.isDoubleSided = true
        material.lightingModel = .blinn
        scene.rootNode.enumerateHierarchy { node, _ in
            node.geometry?.materials = [material]
        }

        let (center, radius) = scene.rootNode.boundingSphere
        let camera = SCNCamera()
        camera.zNear = 0.001
        camera.zFar = Double(max(radius, 1)) * 100
        let cameraNode = SCNNode()
        cameraNode.camera = camera
        let distance = max(radius, 0.001) * 2.6
        cameraNode.position = SCNVector3(center.x, center.y, center.z + distance)
        cameraNode.look(at: center)
        scene.rootNode.addChildNode(cameraNode)
        view.pointOfView = cameraNode
        return scene
    }
}
