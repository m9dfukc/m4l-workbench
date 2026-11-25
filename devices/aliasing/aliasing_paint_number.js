// GENERATED from devices/aliasing/js/src/aliasing_paint_number.ts by tools/js-build.mjs - do not edit.
// Edit the TypeScript source and run tools/check.sh aliasing.

// devices/aliasing/js/src/paint_kit.ts
function hex(h, a) {
  var n = parseInt(h.replace("#", ""), 16);
  return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255, a === void 0 ? 1 : a];
}
function withAlpha(c, a) {
  return [c[0], c[1], c[2], a];
}
function mixColor(a, b, t) {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t];
}
function luminance(c) {
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function palette(dark) {
  if (dark) {
    return {
      dark: true,
      text: hex("#c9c9c9"),
      label: hex("#969696"),
      track: hex("#424242"),
      rule: hex("#2e2e2e"),
      field: hex("#1b1b1b"),
      sel: hex("#d6d6d6"),
      selFg: hex("#1b1b1b"),
      sizeFill: hex("#3a3a3a"),
      write: hex("#e4e4e4"),
      read: hex("#8fa6b6"),
      disp: hex("#151515"),
      voice: hex("#a3a3a3"),
      meter: hex("#9a9a9a")
    };
  }
  return {
    dark: false,
    text: hex("#1e1e1e"),
    label: hex("#4d4d4d"),
    track: hex("#9e9e9e"),
    rule: hex("#c9c9c9"),
    field: hex("#e6e6e6"),
    sel: hex("#2a2a2a"),
    selFg: hex("#efefef"),
    sizeFill: hex("#bdbdbd"),
    write: hex("#242424"),
    read: hex("#41627a"),
    disp: hex("#ececec"),
    voice: hex("#555555"),
    meter: hex("#555555")
  };
}
function themeIsDark(getcolor) {
  if (!getcolor) return true;
  try {
    var c = getcolor("live_control_fg");
    if (c && c.length >= 3) return luminance([Number(c[0]), Number(c[1]), Number(c[2]), 1]) > 0.45;
  } catch (e) {
  }
  return true;
}
function roleOf(varname) {
  var v = String(varname || "");
  if (v.indexOf("w_") === 0 || v.indexOf("tone_band") === 0) return "write";
  if (v.indexOf("r_") === 0 || v.indexOf("tone_res") === 0) return "read";
  return "neutral";
}
function accentFor(role, p) {
  if (role === "write") return p.write;
  if (role === "read") return p.read;
  return p.text;
}
function clamp(x, lo, hi) {
  return x < lo ? lo : x > hi ? hi : x;
}
function firstNumber(v) {
  if (v === null || v === void 0) return NaN;
  if (typeof v === "object" && v.length !== void 0) return v.length ? parseFloat(v[0]) : NaN;
  return parseFloat(v);
}
function normOf(v, lo, hi, exponent) {
  if (!(hi > lo)) return 0;
  var n = clamp((v - lo) / (hi - lo), 0, 1);
  var e = exponent > 0 ? exponent : 1;
  return Math.pow(n, 1 / e);
}
function sprintf1(fmt, v) {
  var out = "";
  var i = 0;
  while (i < fmt.length) {
    var ch = fmt.charAt(i);
    if (ch !== "%") {
      out += ch;
      i++;
      continue;
    }
    var j = i + 1;
    var spec = "";
    while (j < fmt.length && "0123456789.-+ ".indexOf(fmt.charAt(j)) >= 0) {
      spec += fmt.charAt(j);
      j++;
    }
    var conv = fmt.charAt(j);
    if (conv === "%") {
      out += "%";
    } else if (conv === "d" || conv === "i") {
      out += String(Math.round(v));
    } else if (conv === "f") {
      var dot = spec.indexOf(".");
      var prec = dot >= 0 ? parseInt(spec.substring(dot + 1), 10) : 6;
      if (isNaN(prec)) prec = 6;
      out += v.toFixed(prec);
    } else if (conv === "s") {
      out += String(v);
    } else {
      out += "%" + spec + conv;
    }
    i = j + 1;
  }
  return out;
}
function formatHz(f) {
  if (f >= 1e4) return (f / 1e3).toFixed(1) + " kHz";
  if (f >= 1e3) return (f / 1e3).toFixed(2) + " kHz";
  if (f >= 100) return String(Math.round(f)) + " Hz";
  if (f >= 10) return f.toFixed(1) + " Hz";
  return f.toFixed(2) + " Hz";
}
function formatValue(v, unitstyle, units, enumLabels) {
  if (isNaN(v)) return "";
  if (enumLabels && enumLabels.length) {
    var k = clamp(Math.round(v), 0, enumLabels.length - 1);
    return String(enumLabels[k]);
  }
  switch (unitstyle) {
    case 0:
      return String(Math.round(v));
    case 2:
      return v >= 1e3 ? (v / 1e3).toFixed(2) + " s" : v.toFixed(v < 10 ? 2 : 0) + " ms";
    case 3:
      return formatHz(v);
    case 4:
      return (v <= -69.95 ? "-inf" : v.toFixed(1)) + " dB";
    case 5:
      return v.toFixed(Math.abs(v) < 10 ? 1 : 0) + " %";
    case 6:
      return v === 0 ? "C" : Math.abs(Math.round(v)) + (v < 0 ? "L" : "R");
    case 7:
      return (v > 0 ? "+" : "") + Math.round(v) + " st";
    case 9:
      return units ? sprintf1(units, v) : v.toFixed(2);
    default:
      return Math.abs(v) >= 100 ? String(Math.round(v)) : v.toFixed(2);
  }
}
function enumLabelsFrom(range, type) {
  if (type !== 2 || !range || typeof range !== "object" || range.length === void 0) return null;
  var out = [];
  for (var i = 0; i < range.length; i++) out.push(String(range[i]));
  return out.length ? out : null;
}
function iconPath(label) {
  switch (label) {
    case "Ramp":
    case "Saw":
      return [[1, 11], [21, 1], [21, 11]];
    case "Tri":
      return [[1, 11], [11, 1], [21, 11]];
    case "Tri \xB1":
      return [[1, 6], [6, 1], [16, 11], [21, 6]];
    case "=Read":
      return [[1, 11], [7, 5], [13, 9], [21, 1]];
    case "Square":
      return [[1, 11], [1, 1], [11, 1], [11, 11], [21, 11], [21, 1]];
    case "S&H":
      return [[1, 8], [5, 8], [5, 3], [9, 3], [9, 10], [13, 10], [13, 5], [17, 5], [17, 9], [21, 9]];
    case "Sine": {
      var pts = [];
      for (var i = 0; i <= 20; i++) pts.push([1 + i, 6 - 5 * Math.sin(i / 20 * 2 * Math.PI)]);
      return pts;
    }
    case "Random": {
      var r = [6, 2.5, 4, 8, 10.5, 9, 4.5, 3, 6, 5];
      var q = [];
      for (var k = 0; k < r.length; k++) q.push([1 + k * 20 / (r.length - 1), r[k]]);
      return q;
    }
    default:
      return null;
  }
}
function fitText(s, maxw, measure2) {
  if (measure2(s) <= maxw) return s;
  var t = s;
  while (t.length > 1 && measure2(t + ".") > maxw) t = t.substring(0, t.length - 1);
  return t + ".";
}

// devices/aliasing/js/src/paint_max.ts
var FONT = "Ableton Sans Medium";
var FONT_BOLD = "Ableton Sans Bold";
function attr(name) {
  try {
    return box.getattr(name);
  } catch (e) {
    return null;
  }
}
function attrNum(name, fallback) {
  var n = firstNumber(attr(name));
  return isNaN(n) ? fallback : n;
}
function attrStr(name) {
  var a = attr(name);
  if (a === null || a === void 0) return "";
  if (typeof a === "object" && a.length !== void 0) {
    var parts = [];
    for (var i = 0; i < a.length; i++) parts.push(String(a[i]));
    return parts.join(" ");
  }
  return String(a);
}
function getcolorFn() {
  try {
    if (typeof max !== "undefined" && max && typeof max.getcolor === "function") {
      return function(id) {
        return max.getcolor(id);
      };
    }
  } catch (e) {
  }
  return null;
}
function currentPalette() {
  return palette(themeIsDark(getcolorFn()));
}
function varnameOf() {
  try {
    var v = box.varname;
    if (v) return String(v);
  } catch (e) {
  }
  return attrStr("varname");
}
function isActive() {
  return attrNum("active", 1) !== 0;
}
function value() {
  var v = 0;
  try {
    v = box.getvalueof();
  } catch (e) {
  }
  var n = firstNumber(v);
  return isNaN(n) ? 0 : n;
}
function paramInfo() {
  var type = attrNum("_parameter_type", 0);
  var range = attr("_parameter_range");
  var labels = enumLabelsFrom(range, type);
  var lo = 0;
  var hi = 1;
  if (labels) {
    hi = labels.length - 1;
  } else if (range && typeof range === "object" && range.length >= 2) {
    lo = parseFloat(range[0]);
    hi = parseFloat(range[1]);
    if (isNaN(lo) || isNaN(hi)) {
      lo = 0;
      hi = 1;
    }
  }
  return {
    lo: lo,
    hi: hi,
    exponent: attrNum("_parameter_exponent", 1),
    type: type,
    unitstyle: attrNum("_parameter_unitstyle", 1),
    units: attrStr("_parameter_units"),
    labels: labels
  };
}
function setColor(c) {
  mgraphics.set_source_rgba(c[0], c[1], c[2], c[3]);
}
function font(size, bold) {
  mgraphics.select_font_face(bold ? FONT_BOLD : FONT);
  mgraphics.set_font_size(size);
}
function measure(s) {
  return mgraphics.text_measure(s)[0];
}
function text(s, x, y, color, align) {
  var w = measure(s);
  var tx = align === "center" ? x - w / 2 : align === "right" ? x - w : x;
  setColor(color);
  mgraphics.move_to(tx, y);
  mgraphics.show_text(s);
}
function enableAutomationDots() {
  try {
    box.setattr("jspainterautomation", 1);
  } catch (e) {
  }
}
function polyline(pts, x, y, sx, sy) {
  for (var i = 0; i < pts.length; i++) {
    var px = x + pts[i][0] * sx;
    var py = y + pts[i][1] * sy;
    if (i === 0) mgraphics.move_to(px, py);
    else mgraphics.line_to(px, py);
  }
}
function dim(c, active, p) {
  if (active) return c;
  return [c[0], c[1], c[2], c[3] * (p.dark ? 0.4 : 0.45)];
}

// devices/aliasing/js/src/aliasing_paint_number.ts
enableAutomationDots();
function paint() {
  var w = mgraphics.size[0];
  var h = mgraphics.size[1];
  var p = currentPalette();
  var active = isActive();
  var info = paramInfo();
  var v = value();
  setColor(dim(p.field, active, p));
  mgraphics.rectangle_rounded(0, 0, w, h, 6, 6);
  mgraphics.fill();
  font(9, false);
  text(fitText(formatValue(v, info.unitstyle, info.units, info.labels), w - 4, measure), w / 2, h / 2 + 3, dim(p.text, active, p), "center");
}
