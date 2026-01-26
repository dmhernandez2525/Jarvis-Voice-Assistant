// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "JarvisApp",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "JarvisApp", targets: ["JarvisApp"])
    ],
    dependencies: [
        // WebSocket for PersonaPlex
        .package(url: "https://github.com/vapor/websocket-kit.git", from: "2.14.0"),
        // HotKey for global keyboard shortcuts
        .package(url: "https://github.com/soffes/HotKey.git", from: "0.2.0"),
    ],
    targets: [
        .executableTarget(
            name: "JarvisApp",
            dependencies: [
                .product(name: "WebSocketKit", package: "websocket-kit"),
                .product(name: "HotKey", package: "HotKey"),
            ],
            path: "Sources",
            resources: [
                .process("../Resources")
            ]
        )
    ]
)
