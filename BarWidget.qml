import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

BarWidget {
  id: root
  moduleName: "dorneles.omapod"

  // Settings dynamically read from root.settings (persisted in shell.json)
  readonly property string currentDisplayFormat: setting("displayFormat", "icon_only")
  readonly property string currentIconStyle: setting("iconStyle", "rocket")
  readonly property string currentApiKey: setting("apiKey", "DEMO_KEY")

  // State parsed from ~/.cache/omarchy-nasa-apod/state.json
  property var apodState: null
  property bool isFetching: fetchProcess.running || actionProcess.running

  readonly property string activeIcon: Model.getIcon(currentIconStyle)
  readonly property string barTitle: Model.formatBarText(apodState, currentDisplayFormat, 30)
  readonly property string fullLabel: currentDisplayFormat === "icon_only"
    ? activeIcon
    : (activeIcon + (barTitle !== "" ? " " + barTitle : ""))

  readonly property string scriptPath: Qt.resolvedUrl("scripts/apod.py").toString().replace(/^file:\/\//, "")

  readonly property string tooltipInfo: {
    if (!apodState || !apodState.success) {
      return "NASA • Astronomy Picture of the Day (APOD)\n Click to view today's photo"
    }
    return "NASA • Astronomy Picture of the Day\n" +
      " " + (apodState.title || "") + "\n" +
      "󰃭 " + (apodState.formatted_date || apodState.date || "") +
      (apodState.copyright ? ("\n󰄬 " + apodState.copyright) : "") + "\n" +
      "──────────────────────────\n" +
      "• Click: Open NASA APOD panel\n" +
      "• Middle-click: Random photo"
  }

  function injectPanel() {
    var target = panelLoader.item
    if (!target) return
    if ("bar" in target) target.bar = root.bar
    if ("settings" in target) target.settings = root.settings
    if ("anchorItem" in target) target.anchorItem = barButton
    if ("hostWidget" in target) target.hostWidget = root
    if ("scriptPath" in target) target.scriptPath = root.scriptPath
  }

  onBarChanged: injectPanel()
  onSettingsChanged: injectPanel()

  // Panel coordination
  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false

  function open() {
    if (panelLoader.item) panelLoader.item.open()
  }

  function close() {
    if (panelLoader.item) panelLoader.item.close()
  }

  function togglePanel() {
    if (panelLoader.item) panelLoader.item.toggle()
  }

  readonly property bool popoutSwitchClosing: panelLoader.item ? panelLoader.item.popoutSwitchClosing === true : false

  function closeForPopoutSwitch() {
    if (panelLoader.item) panelLoader.item.closeForPopoutSwitch()
  }

  // API & Action methods
  function fetchToday(force) {
    if (fetchProcess.running) return
    var args = ["python3", root.scriptPath, "fetch", "--today", "--api-key", root.currentApiKey]
    if (force) args.push("--force")
    fetchProcess.command = args
    fetchProcess.running = true
  }

  function fetchDate(targetDate) {
    if (!targetDate || fetchProcess.running) return
    fetchProcess.command = ["python3", root.scriptPath, "fetch", "--date", targetDate, "--api-key", root.currentApiKey]
    fetchProcess.running = true
  }

  function fetchRandom() {
    if (fetchProcess.running) return
    fetchProcess.command = ["python3", root.scriptPath, "fetch", "--random", "--api-key", root.currentApiKey]
    fetchProcess.running = true
  }

  function viewImage() {
    if (actionProcess.running) return
    root.close()
    actionProcess.command = ["python3", root.scriptPath, "view"]
    actionProcess.running = true
  }

  function playMedia() {
    if (actionProcess.running) return
    actionProcess.command = ["python3", root.scriptPath, "play"]
    actionProcess.running = true
  }

  function setWallpaper() {
    if (actionProcess.running) return
    actionProcess.command = ["python3", root.scriptPath, "wallpaper"]
    actionProcess.running = true
  }

  function saveImage() {
    if (actionProcess.running) return
    actionProcess.command = ["python3", root.scriptPath, "save"]
    actionProcess.running = true
  }

  function openInBrowser() {
    if (actionProcess.running) return
    actionProcess.command = ["python3", root.scriptPath, "browser"]
    actionProcess.running = true
  }

  function copyImage(kind) {
    if (actionProcess.running) return
    actionProcess.command = ["python3", root.scriptPath, "copy", "--kind", kind || "image"]
    actionProcess.running = true
  }

  function cycleFormat() {
    var next = Model.nextFormat(currentDisplayFormat)
    updateSetting("displayFormat", next)
  }

  function cycleIconStyle() {
    var next = Model.nextIconStyle(currentIconStyle)
    updateSetting("iconStyle", next)
  }

  function updateSetting(key, val) {
    var entry = { id: root.moduleName }
    for (var k in root.settings) if (k !== "id") entry[k] = root.settings[k]
    entry[key] = val
    root.settings = entry

    if (root.bar && root.bar.shell && typeof root.bar.shell.updateEntryInline === "function") {
      root.bar.shell.updateEntryInline(root.moduleName, entry)
    }
  }

  // Watch state.json for updates
  property FileView stateFile: FileView {
    path: Quickshell.env("HOME") + "/.cache/omarchy-omapod/state.json"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: {
      try {
        var parsed = JSON.parse(text())
        if (parsed && typeof parsed === "object") {
          root.apodState = parsed
        }
      } catch (e) {}
    }
  }

  Component.onCompleted: {
    stateFile.reload()
    if (!root.apodState || !root.apodState.success) {
      root.fetchToday(false)
    }
  }

  // Background fetch process
  Process {
    id: fetchProcess
    running: false
    onExited: function(code, status) {
      stateFile.reload()
    }
  }

  // Background action process
  Process {
    id: actionProcess
    running: false
    onExited: function(code, status) {
      stateFile.reload()
    }
  }

  // Hourly auto-sync check
  Timer {
    interval: 3 * 3600 * 1000 // every 3 hours
    repeat: true
    running: true
    onTriggered: root.fetchToday(false)
  }

  // Midnight day rollover detection
  property int lastSeenDay: new Date().getDate()
  SystemClock {
    id: minuteClock
    precision: SystemClock.Minutes
    onDateChanged: {
      var curDay = new Date().getDate()
      if (curDay !== root.lastSeenDay) {
        root.lastSeenDay = curDay
        root.fetchToday(true)
      }
    }
  }

  // IPC handler for CLI and scripting triggers
  IpcHandler {
    target: "dorneles.omapod"

    function toggle(): void { root.togglePanel() }
    function open(): void { root.open() }
    function close(): void { root.close() }
    function play(): void { root.playMedia() }
    function refresh(): void { root.fetchToday(true) }
    function random(): void { root.fetchRandom() }
    function wallpaper(): void { root.setWallpaper() }
    function save(): void { root.saveImage() }
    function copy(): void { root.copyImage("image") }
    function browser(): void { root.openInBrowser() }
  }

  // Loader for popup panel
  Loader {
    id: panelLoader
    active: true
    source: Qt.resolvedUrl("Panel.qml")
    visible: false
    onLoaded: {
      root.injectPanel()
      Qt.callLater(root.injectPanel)
    }
  }

  // Bar Widget Layout
  implicitWidth: barButton.implicitWidth
  implicitHeight: barButton.implicitHeight

  WidgetButton {
    id: barButton
    anchors.fill: parent
    bar: root.bar
    text: root.fullLabel
    active: root.opened
    fontSize: root.currentDisplayFormat === "icon_only" ? Style.bar.iconFont : Style.font.body
    tooltipText: root.tooltipInfo

    onPressed: function(btn) {
      if (btn === Qt.MiddleButton) {
        root.fetchRandom()
      } else {
        root.togglePanel()
      }
    }
  }
}
