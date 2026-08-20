// Model.js - Helper methods for NASA APOD plugin

function getIcon(iconStyle) {
  switch (iconStyle) {
    case "rocket_launch":
      return "󰛓" // nf-md-rocket_launch
    case "telescope":
      return "󰭎" // nf-md-telescope
    case "planet":
      return "󰻌" // nf-md-earth
    case "star":
      return "󰓏" // nf-md-star_four_points
    case "rocket":
    default:
      return "" // nf-fa-rocket (classic iconic rocket)
  }
}

function truncateText(text, maxLen) {
  if (!text) return ""
  var str = String(text).trim()
  if (str.length <= maxLen) return str
  return str.slice(0, maxLen - 1) + "…"
}

function formatBarText(state, displayFormat, maxTitleLength) {
  if (displayFormat === "icon_only" || !state) return ""
  var title = state.title || ""
  var limit = Number(maxTitleLength) || 28
  return truncateText(title, limit)
}

function formatDateDisplay(isoDate) {
  if (!isoDate) return ""
  try {
    var parts = isoDate.split("-")
    if (parts.length === 3) {
      var d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10))
      var months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
      ]
      return months[d.getMonth()] + " " + parseInt(parts[2], 10) + ", " + parts[0]
    }
  } catch (e) {}
  return isoDate
}

function nextFormat(current) {
  var formats = ["icon_only", "icon_title"]
  var idx = formats.indexOf(current)
  return formats[(idx + 1) % formats.length]
}

function nextIconStyle(current) {
  var styles = ["rocket", "rocket_launch", "telescope", "planet", "star"]
  var idx = styles.indexOf(current)
  return styles[(idx + 1) % styles.length]
}

if (typeof module !== "undefined") {
  module.exports = {
    getIcon: getIcon,
    truncateText: truncateText,
    formatBarText: formatBarText,
    formatDateDisplay: formatDateDisplay,
    nextFormat: nextFormat,
    nextIconStyle: nextIconStyle
  }
}
