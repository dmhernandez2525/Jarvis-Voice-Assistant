import Cocoa

// Create and run the application
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate

// Required for menu bar apps - no dock icon, menu bar only
app.setActivationPolicy(.accessory)

app.run()
