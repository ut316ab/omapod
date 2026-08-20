import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

Panel {
  id: root
  moduleName: "dorneles.omapod"
  ipcTarget: "dorneles.omapod"
  manageIpc: false

  property var anchorItem: null
  property var hostWidget: null
  property string scriptPath: ""
  property bool isMuted: false

  // Reactive bindings directly to hostWidget
  readonly property var apodState: hostWidget ? hostWidget.apodState : null
  readonly property bool isFetching: hostWidget ? hostWidget.isFetching : false
  readonly property bool isVideo: apodState && apodState.media_type === "video"
  readonly property bool isDirectVideo: isVideo && apodState && (String(apodState.url || "").indexOf(".mp4") !== -1 || (apodState.local_video && apodState.local_video !== ""))
  readonly property bool isVideoPlaying: isDirectVideo && mediaViewer.playbackState === MediaPlayer.PlayingState

  readonly property var barIdentity: hostWidget || root
  readonly property color foreground: bar ? bar.barForeground : Color.foreground
  readonly property color dim: Qt.darker(foreground, 1.35)
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family

  function open() {
    root.controller.show()
  }

  function close() {
    if (mediaViewer.playbackState === MediaPlayer.PlayingState) {
      mediaViewer.pause()
    }
    root.controller.hide()
  }

  function toggle() {
    if (root.opened) root.close()
    else root.open()
  }

  function switchPanel(direction) {
    if (root.bar && typeof root.bar.switchPanelFrom === "function") {
      return root.bar.switchPanelFrom(root.barIdentity, direction)
    }
    return false
  }

  function togglePlayVideo() {
    if (!root.isVideo) return
    if (root.isDirectVideo) {
      if (mediaViewer.playbackState === MediaPlayer.PlayingState) {
        mediaViewer.pause()
      } else {
        mediaViewer.play()
      }
    } else {
      if (root.hostWidget) root.hostWidget.playMedia()
    }
  }

  function formatTime(ms) {
    if (isNaN(ms) || ms <= 0) return "00:00"
    var totalSec = Math.floor(ms / 1000)
    var m = Math.floor(totalSec / 60)
    var s = totalSec % 60
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s
  }

  onOpenedChanged: {
    if (!root.opened && mediaViewer.playbackState === MediaPlayer.PlayingState) {
      mediaViewer.pause()
    }
  }

  onApodStateChanged: {
    mediaViewer.stop()
  }

  // Embedded QtQuick MediaPlayer for inline direct video playback
  MediaPlayer {
    id: mediaViewer
    source: {
      if (!root.isDirectVideo || !root.apodState) return ""
      if (root.apodState.local_video && root.apodState.local_video !== "") return "file://" + root.apodState.local_video
      if (root.apodState.url && String(root.apodState.url).indexOf("http") === 0) return String(root.apodState.url)
      return ""
    }
    audioOutput: AudioOutput {
      id: audioOut
      volume: root.isMuted ? 0.0 : 0.8
      muted: root.isMuted
    }
    videoOutput: videoOutputItem
    loops: MediaPlayer.Infinite

    onErrorOccurred: function(error, errorString) {
      console.warn("NASA APOD MediaPlayer error:", errorString)
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem || root
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(490))
    contentHeight: panel.fittedContentHeight(contentColumn.implicitHeight, Style.space(660))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent

      onMoveRequested: function(dx, dy) {
        if (dx < 0 && root.apodState && root.apodState.prev_date && root.hostWidget) {
          mediaViewer.stop()
          root.hostWidget.fetchDate(root.apodState.prev_date)
        } else if (dx > 0 && root.apodState && root.apodState.next_date && !root.apodState.is_today && root.hostWidget) {
          mediaViewer.stop()
          root.hostWidget.fetchDate(root.apodState.next_date)
        } else if (dy !== 0) {
          scrollFlick.contentY = Math.max(0, Math.min(
            scrollFlick.contentY + dy * Style.space(60),
            Math.max(0, scrollFlick.contentHeight - scrollFlick.height)
          ))
        }
      }

      onActivateRequested: {
        if (root.isVideo) root.togglePlayVideo()
        else if (root.hostWidget) {
          root.close()
          root.hostWidget.viewImage()
        }
      }
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      onTextKey: function(t) {
        var key = String(t || "").toLowerCase()
        if (key === "p" || key === " ") root.togglePlayVideo()
        else if (key === "i" && !root.isVideo && root.hostWidget) {
          root.close()
          root.hostWidget.viewImage()
        }
        else if (key === "m") root.isMuted = !root.isMuted
        else if (key === "r" && root.hostWidget) { mediaViewer.stop(); root.hostWidget.fetchRandom() }
        else if (key === "t" && root.hostWidget) { mediaViewer.stop(); root.hostWidget.fetchToday(false) }
        else if (key === "w" && root.hostWidget) root.hostWidget.setWallpaper()
        else if (key === "s" && root.hostWidget) root.hostWidget.saveImage()
        else if (key === "v" && root.hostWidget) root.hostWidget.playMedia()
        else if (key === "b" && root.hostWidget) root.hostWidget.openInBrowser()
        else if (key === "c" && root.hostWidget && !root.isVideo) root.hostWidget.copyImage("image")
      }

      Flickable {
        id: scrollFlick
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        interactive: contentHeight > height
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        Column {
          id: contentColumn
          width: scrollFlick.width
          spacing: Style.space(12)

          // -------------------------------------------------------------
          // Hero Header
          // -------------------------------------------------------------
          PanelHero {
            width: parent.width
            title: "omapod"
            meta: "ASTRONOMY PICTURE OF THE DAY"
            foreground: root.foreground
            fontFamily: root.fontFamily

            iconComponent: Component {
              Text {
                text: "" // nf-fa-rocket (classic rocket ship)
                font.family: root.fontFamily
                font.pixelSize: Style.font.display
                color: Color.accent
              }
            }

            trailingControl: Component {
              Row {
                spacing: Style.space(6)

                Button {
                  iconText: "󰒝" // shuffle
                  tooltipText: "Random Date (R)"
                  fontSize: Style.font.body
                  onClicked: if (root.hostWidget) { mediaViewer.stop(); root.hostWidget.fetchRandom() }
                }

                Button {
                  iconText: "󰑐" // refresh / sync
                  iconSpinning: root.isFetching
                  tooltipText: "Refresh (T)"
                  fontSize: Style.font.body
                  onClicked: if (root.hostWidget) { mediaViewer.stop(); root.hostWidget.fetchToday(true) }
                }

                Button {
                  iconText: "󰅖" // close
                  tooltipText: "Close (Esc)"
                  fontSize: Style.font.body
                  onClicked: root.close()
                }
              }
            }
          }

          PanelSeparator { foreground: root.foreground }

          // -------------------------------------------------------------
          // Date Navigation Bar
          // -------------------------------------------------------------
          Row {
            width: parent.width
            spacing: Style.space(6)

            Button {
              width: (parent.width - Style.space(18)) / 4
              iconText: "󰅁" // chevron left
              text: "Previous"
              tooltipText: "Previous Day (Left Arrow)"
              fontSize: Style.font.caption
              enabled: root.apodState && root.apodState.prev_date !== null && !root.isFetching
              opacity: enabled ? 1.0 : 0.35
              Behavior on opacity { NumberAnimation { duration: 120 } }
              onClicked: if (enabled && root.hostWidget && root.apodState) { mediaViewer.stop(); root.hostWidget.fetchDate(root.apodState.prev_date) }
            }

            Button {
              width: (parent.width - Style.space(18)) / 4
              iconText: "󰃭" // calendar today
              text: "Today"
              tooltipText: "Today's Picture (T)"
              fontSize: Style.font.caption
              selected: root.apodState && root.apodState.is_today
              enabled: !root.isFetching
              opacity: enabled ? 1.0 : 0.35
              Behavior on opacity { NumberAnimation { duration: 120 } }
              onClicked: if (enabled && root.hostWidget) { mediaViewer.stop(); root.hostWidget.fetchToday(false) }
            }

            Button {
              width: (parent.width - Style.space(18)) / 4
              iconText: "󰅂" // chevron right
              text: "Next"
              tooltipText: "Next Day (Right Arrow)"
              fontSize: Style.font.caption
              enabled: root.apodState && root.apodState.next_date !== null && !root.apodState.is_today && !root.isFetching
              opacity: enabled ? 1.0 : 0.35
              Behavior on opacity { NumberAnimation { duration: 120 } }
              onClicked: if (enabled && root.hostWidget && root.apodState && !root.apodState.is_today) { mediaViewer.stop(); root.hostWidget.fetchDate(root.apodState.next_date) }
            }

            Button {
              width: (parent.width - Style.space(18)) / 4
              iconText: "󰒝" // shuffle
              text: "Random"
              tooltipText: "Random Date (R)"
              fontSize: Style.font.caption
              enabled: !root.isFetching
              opacity: enabled ? 1.0 : 0.35
              Behavior on opacity { NumberAnimation { duration: 120 } }
              onClicked: if (enabled && root.hostWidget) { mediaViewer.stop(); root.hostWidget.fetchRandom() }
            }
          }

          // -------------------------------------------------------------
          // Featured Media Container (Image / Video Preview)
          // -------------------------------------------------------------
          Rectangle {
            id: mediaFrame
            width: parent.width
            height: Style.space(250)
            radius: Style.cornerRadius
            color: "#000000"
            border.width: 1
            border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.12)
            clip: true

            // Loading state
            Column {
              anchors.centerIn: parent
              spacing: Style.space(8)
              visible: root.isFetching

              Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "󰑐"
                font.family: root.fontFamily
                font.pixelSize: Style.font.display
                color: Color.accent
              }

              Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Fetching NASA astronomy data..."
                color: root.foreground
                font.family: root.fontFamily
                font.pixelSize: Style.font.body
                font.bold: true
              }
            }

            // Image Display (Thumbnail or Photo)
            Image {
              id: apodImage
              anchors.fill: parent
              visible: !root.isFetching && root.apodState && root.apodState.success && (!root.isVideo || (root.apodState.local_image && root.apodState.local_image !== "")) && mediaViewer.playbackState !== MediaPlayer.PlayingState
              source: {
                if (root.isFetching || !root.apodState || !root.apodState.success) return ""
                if (root.apodState.local_image && root.apodState.local_image !== "") return "file://" + root.apodState.local_image
                if (!root.isVideo && root.apodState.url) return root.apodState.url
                return ""
              }
              fillMode: Image.PreserveAspectCrop
              asynchronous: true
              cache: false
            }

            // Video Output Item (Embedded Video Player)
            VideoOutput {
              id: videoOutputItem
              anchors.fill: parent
              fillMode: VideoOutput.PreserveAspectFit
              visible: !root.isFetching && root.isVideo && (mediaViewer.playbackState === MediaPlayer.PlayingState || mediaViewer.playbackState === MediaPlayer.PausedState)
            }

            // Video Play Overlay Banner (when paused/stopped)
            Rectangle {
              anchors.fill: parent
              visible: !root.isFetching && root.apodState && root.apodState.success && root.isVideo && mediaViewer.playbackState !== MediaPlayer.PlayingState
              color: apodImage.visible ? Qt.rgba(0, 0, 0, 0.40) : Qt.rgba(15/255, 20/255, 35/255, 0.95)

              Column {
                anchors.centerIn: parent
                spacing: Style.space(10)

                Rectangle {
                  anchors.horizontalCenter: parent.horizontalCenter
                  width: Style.space(60)
                  height: Style.space(60)
                  radius: width / 2
                  color: Color.accent

                  Text {
                    anchors.centerIn: parent
                    text: "󰐊" // play
                    color: "#ffffff"
                    font.family: root.fontFamily
                    font.pixelSize: Style.font.title
                  }
                }

                Text {
                  anchors.horizontalCenter: parent.horizontalCenter
                  text: root.isDirectVideo ? "Astronomy Video • Click to Play" : "Astronomy Video • Click to Watch in Player"
                  color: "#ffffff"
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.body
                  font.bold: true
                }
              }
            }

            // Video Controls Bottom Bar (visible when direct video is playing or paused)
            Rectangle {
              id: videoControlsBar
              anchors.left: parent.left
              anchors.right: parent.right
              anchors.bottom: parent.bottom
              height: Style.space(38)
              visible: !root.isFetching && root.isDirectVideo && (mediaViewer.playbackState === MediaPlayer.PlayingState || mediaViewer.playbackState === MediaPlayer.PausedState)
              color: Qt.rgba(0, 0, 0, 0.80)

              RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Style.space(8)
                anchors.rightMargin: Style.space(8)
                spacing: Style.space(6)

                // Play / Pause Button
                Button {
                  iconText: mediaViewer.playbackState === MediaPlayer.PlayingState ? "󰏤" : "󰐊" // pause / play
                  tooltipText: mediaViewer.playbackState === MediaPlayer.PlayingState ? "Pause (Space)" : "Play (Space)"
                  fontSize: Style.font.caption
                  onClicked: root.togglePlayVideo()
                }

                // Time Indicator
                Text {
                  text: root.formatTime(mediaViewer.position) + " / " + root.formatTime(mediaViewer.duration)
                  color: "#ffffff"
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.caption
                  font.bold: true
                }

                // Progress Bar
                Rectangle {
                  Layout.fillWidth: true
                  height: Style.space(6)
                  radius: 3
                  color: Qt.rgba(255, 255, 255, 0.25)

                  Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    radius: parent.radius
                    color: Color.accent
                    width: mediaViewer.duration > 0 ? (parent.width * (mediaViewer.position / mediaViewer.duration)) : 0
                  }

                  MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: function(mouse) {
                      if (mediaViewer.duration > 0 && width > 0) {
                        var ratio = Math.max(0, Math.min(1, mouse.x / width))
                        mediaViewer.position = Math.round(ratio * mediaViewer.duration)
                      }
                    }
                  }
                }

                // Mute / Unmute Button
                Button {
                  iconText: root.isMuted ? "󰖁" : "󰕾" // mute / volume
                  tooltipText: root.isMuted ? "Unmute Audio (M)" : "Mute Audio (M)"
                  fontSize: Style.font.caption
                  onClicked: root.isMuted = !root.isMuted
                }

                // External MPV Player Button
                Button {
                  iconText: "󰕧" // video / external
                  tooltipText: "Open in External MPV Player (V)"
                  fontSize: Style.font.caption
                  onClicked: if (root.hostWidget) { mediaViewer.pause(); root.hostWidget.playMedia() }
                }
              }
            }

            // Error View
            Column {
              anchors.centerIn: parent
              spacing: Style.space(8)
              visible: !root.isFetching && (!root.apodState || !root.apodState.success)

              Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "󰅙" // error
                font.family: root.fontFamily
                font.pixelSize: Style.font.display
                color: Color.urgent
              }

              Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.apodState && root.apodState.error ? root.apodState.error : "Could not load NASA astronomy picture."
                color: Color.urgent
                font.family: root.fontFamily
                font.pixelSize: Style.font.body
                horizontalAlignment: Text.AlignHCenter
                width: mediaFrame.width - Style.space(32)
                wrapMode: Text.WordWrap
              }

              Button {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Try Again"
                iconText: "󰑐"
                onClicked: if (root.hostWidget) root.hostWidget.fetchToday(true)
              }
            }

            // Hover Overlay for Image (Zoom Indicator)
            Rectangle {
              anchors.fill: parent
              visible: !root.isFetching && !root.isVideo && apodImage.visible && mediaFrameArea.containsMouse
              color: Qt.rgba(0, 0, 0, 0.35)

              Row {
                anchors.centerIn: parent
                spacing: Style.space(8)

                Rectangle {
                  width: Style.space(42)
                  height: Style.space(42)
                  radius: width / 2
                  color: Qt.rgba(0, 0, 0, 0.70)
                  border.width: 1
                  border.color: Qt.rgba(255, 255, 255, 0.25)

                  Text {
                    anchors.centerIn: parent
                    text: "󰍉" // search-plus / zoom
                    color: "#ffffff"
                    font.family: root.fontFamily
                    font.pixelSize: Style.font.title
                  }
                }

                Text {
                  anchors.verticalCenter: parent.verticalCenter
                  text: "Click to View Full Size (I)"
                  color: "#ffffff"
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.body
                  font.bold: true
                }
              }
            }

            // Click to toggle inline video playback OR view full image in external viewer
            MouseArea {
              id: mediaFrameArea
              anchors.fill: parent
              anchors.bottomMargin: videoControlsBar.visible ? videoControlsBar.height : 0
              enabled: !root.isFetching && root.apodState && root.apodState.success
              hoverEnabled: true
              cursorShape: Qt.PointingHandCursor
              onClicked: {
                if (root.isVideo) {
                  root.togglePlayVideo()
                } else if (root.hostWidget) {
                  root.close()
                  root.hostWidget.viewImage()
                }
              }
            }
          }

          // -------------------------------------------------------------
          // Title & Info Card
          // -------------------------------------------------------------
          Column {
            width: parent.width
            spacing: Style.space(4)
            visible: root.apodState && root.apodState.title

            Text {
              width: parent.width
              text: root.apodState ? root.apodState.title : ""
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.subtitle
              font.bold: true
              wrapMode: Text.WordWrap
            }

            Text {
              width: parent.width
              text: root.apodState ? (root.apodState.formatted_date || root.apodState.date || "") : ""
              color: Color.accent
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
              font.bold: true
              visible: text !== ""
            }

            Text {
              width: parent.width
              text: root.apodState && root.apodState.copyright ? ("Photo: " + root.apodState.copyright) : "Credit: NASA / APOD"
              color: root.dim
              font.family: root.fontFamily
              font.pixelSize: Style.font.caption
              font.italic: true
              elide: Text.ElideRight
            }
          }

          // -------------------------------------------------------------
          // Description / Explanation Card
          // -------------------------------------------------------------
          Rectangle {
            width: parent.width
            implicitHeight: explanationText.implicitHeight + Style.space(16)
            radius: Style.cornerRadius
            color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.035)
            border.width: 1
            border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.08)
            visible: root.apodState && root.apodState.explanation

            Text {
              id: explanationText
              anchors.fill: parent
              anchors.margins: Style.space(8)
              text: root.apodState ? root.apodState.explanation : ""
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.bodySmall || Style.font.caption
              lineHeight: 1.3
              wrapMode: Text.WordWrap
            }
          }

          PanelSeparator { foreground: root.foreground }

          // -------------------------------------------------------------
          // Action Toolbar Buttons
          // -------------------------------------------------------------
          Row {
            width: parent.width
            spacing: Style.space(6)

            // Play / Pause button for videos OR Wallpaper button for images
            Button {
              visible: root.isVideo
              width: (parent.width - Style.space(18)) / 4
              iconText: root.isDirectVideo ? (root.isVideoPlaying ? "󰏤" : "󰐊") : "󰐊"
              text: root.isDirectVideo ? (root.isVideoPlaying ? "Pause" : "Play") : "Watch"
              tooltipText: root.isDirectVideo ? "Play/Pause Video (Space / P)" : "Watch Video in MPV Player (Space / P)"
              fontSize: Style.font.caption
              selected: true
              enabled: !root.isFetching
              opacity: enabled ? 1.0 : 0.35
              Behavior on opacity { NumberAnimation { duration: 120 } }
              onClicked: if (enabled) root.togglePlayVideo()
            }

            Button {
              visible: !root.isVideo
              width: (parent.width - Style.space(18)) / 4
              iconText: "󰸉" // wallpaper
              text: "Wallpaper"
              tooltipText: "Set as Desktop Wallpaper (W)"
              fontSize: Style.font.caption
              enabled: root.apodState && !root.isVideo && !root.isFetching
              opacity: enabled ? 1.0 : 0.35
              Behavior on opacity { NumberAnimation { duration: 120 } }
              onClicked: if (enabled && root.hostWidget) root.hostWidget.setWallpaper()
            }

            // MPV player button for videos OR Save button for images
            Button {
              visible: root.isVideo
              width: (parent.width - Style.space(18)) / 4
              iconText: "󰕧" // video / mpv
              text: "MPV"
              tooltipText: "Open in External MPV Player (V)"
              fontSize: Style.font.caption
              enabled: !root.isFetching
              opacity: enabled ? 1.0 : 0.35
              Behavior on opacity { NumberAnimation { duration: 120 } }
              onClicked: if (enabled && root.hostWidget) { if (root.isDirectVideo) mediaViewer.pause(); root.hostWidget.playMedia() }
            }

            Button {
              visible: !root.isVideo
              width: (parent.width - Style.space(18)) / 4
              iconText: "󰆓" // save
              text: "Save"
              tooltipText: "Save Image to ~/Pictures/NASA_APOD (S)"
              fontSize: Style.font.caption
              enabled: root.apodState && !root.isVideo && !root.isFetching
              opacity: enabled ? 1.0 : 0.35
              Behavior on opacity { NumberAnimation { duration: 120 } }
              onClicked: if (enabled && root.hostWidget) root.hostWidget.saveImage()
            }

            Button {
              width: (parent.width - Style.space(18)) / 4
              iconText: "󰖟" // web / browser
              text: "Browser"
              tooltipText: "Open Official NASA Webpage (B)"
              fontSize: Style.font.caption
              enabled: root.apodState && root.apodState.success && !root.isFetching
              opacity: enabled ? 1.0 : 0.35
              Behavior on opacity { NumberAnimation { duration: 120 } }
              onClicked: if (enabled && root.hostWidget) root.hostWidget.openInBrowser()
            }

            Button {
              width: (parent.width - Style.space(18)) / 4
              iconText: "󰅍" // copy
              text: "Copy"
              tooltipText: root.isVideo ? "Copy unavailable for video" : "Copy Image to Clipboard (C)"
              fontSize: Style.font.caption
              enabled: root.apodState && !root.isVideo && !root.isFetching
              opacity: enabled ? 1.0 : 0.35
              Behavior on opacity { NumberAnimation { duration: 120 } }
              onClicked: if (enabled && root.hostWidget && !root.isVideo) root.hostWidget.copyImage("image")
            }
          }
        }
      }
    }
  }
}
