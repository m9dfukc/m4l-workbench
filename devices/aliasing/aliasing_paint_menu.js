// GENERATED from devices/aliasing/js/src/aliasing_paint_menu.ts by tools/js-build.mjs - do not edit.
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
      text: hex("#d2d2d2"),
      label: hex("#b0b0b0"),
      track: hex("#5c5c5c"),
      dialTrack: hex("#747474"),
      rule: hex("#2a2a2a"),
      field: hex("#262626"),
      sel: hex("#d6d6d6"),
      selFg: hex("#1b1b1b"),
      sizeFill: hex("#4c4c4c"),
      write: hex("#e4e4e4"),
      read: hex("#8fb0c4"),
      disp: hex("#161616"),
      voice: hex("#a6a6a6"),
      meter: hex("#9a9a9a"),
      slot: hex("#393939")
    };
  }
  return {
    dark: false,
    text: hex("#111111"),
    label: hex("#262626"),
    track: hex("#6e6e6e"),
    dialTrack: hex("#5a5a5a"),
    rule: hex("#d0d0d0"),
    field: hex("#dedede"),
    sel: hex("#1f1f1f"),
    selFg: hex("#efefef"),
    sizeFill: hex("#bdbdbd"),
    write: hex("#1c1c1c"),
    read: hex("#2f5873"),
    disp: hex("#ececec"),
    voice: hex("#4a4a4a"),
    meter: hex("#3c3c3c"),
    slot: hex("#8c8c8c")
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
  if (v.indexOf("mod_") === 0) {
    var t = v.substring(v.lastIndexOf("_") + 1);
    if (t === "wp" || t === "sy" || t === "wa") return "write";
    if (t === "rp" || t === "sp") return "read";
    return "neutral";
  }
  if (v.indexOf("w_") === 0) return "write";
  if (v.indexOf("r_") === 0) return "read";
  var key = v.substring(v.indexOf("_") + 1);
  if (key.indexOf("band_") === 0) return "write";
  if (key.indexOf("res_") === 0) return "read";
  return "neutral";
}
var FONT_SIZE = 9.5;
function baselineOf(h) {
  return Math.round(h) + 8 >> 1;
}
function compactValue(s, maxw, measure2) {
  if (measure2(s) <= maxw) return s;
  var t = s.replace(/(\d) (?=[^\d\s])/g, "$1");
  if (measure2(t) <= maxw) return t;
  t = t.replace(/(\.\d*?)0+(?=\D|$)/g, "$1").replace(/\.(?=\D|$)/g, "");
  if (measure2(t) <= maxw) return t;
  return fitText(t, maxw, measure2);
}
function fitName(s, maxw, measure2) {
  if (measure2(s) <= maxw) return s;
  var t = s.substring(0, 3);
  if (s.length > 3 && measure2(t) <= maxw) return t;
  return fitText(s, maxw, measure2);
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
function writeIcon(label) {
  switch (label) {
    case "Ramp":
      return [[1, 11], [21, 1], [21, 11]];
    case "Tri":
      return [[1, 11], [11, 1], [21, 11]];
    case "Tri \xB1":
      return [[1, 11], [6, 11], [11, 1], [16, 11], [21, 11]];
    case "Sine": {
      var pts = [];
      for (var i = 0; i <= 20; i++) pts.push([1 + i, 11 - 10 * (0.5 - 0.5 * Math.cos(i / 20 * 2 * Math.PI))]);
      return pts;
    }
    case "Pulse":
      return [[1, 11], [11, 11], [11, 1], [21, 1]];
    case "Pulsar":
      return [[1, 11], [9, 1], [9, 11], [21, 11]];
    case "Spike":
      return [[1, 11], [5, 1], [9, 11], [21, 11]];
    case "Noise":
      return [[1, 7], [4, 7], [4, 2], [7, 2], [7, 9], [10, 9], [10, 4], [13, 4], [13, 10], [16, 10], [16, 3], [19, 3], [19, 6], [21, 6]];
    default:
      return null;
  }
}
function iconPath(label, family) {
  if (family === "write") return writeIcon(label);
  switch (label) {
    case "Ramp":
    case "Saw":
      return [[1, 11], [21, 1], [21, 11]];
    case "Tri":
      return [[1, 11], [11, 1], [21, 11]];
    case "Tri \xB1":
      return [[1, 6], [6, 1], [16, 11], [21, 6]];
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
  mgraphics.move_to(Math.round(tx), Math.round(y));
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

// devices/aliasing/js/src/aliasing_paint_menu.ts
enableAutomationDots();
function paint() {
  var w = mgraphics.size[0];
  var h = mgraphics.size[1];
  var p = currentPalette();
  var active = isActive();
  var info = paramInfo();
  var labels = info.labels || [];
  var k = Math.round(value());
  var label = k >= 0 && k < labels.length ? labels[k] : String(k);
  setColor(dim(p.field, active, p));
  mgraphics.rectangle_rounded(0, 0, w, h, 6, 6);
  mgraphics.fill();
  font(h >= 15 ? FONT_SIZE : 9, false);
  var marked = label.length > 2 && label.substring(label.length - 2) === " \u2022";
  if (marked) label = label.substring(0, label.length - 2);
  var shown = fitText(label, w - (marked ? 26 : 18), measure);
  text(shown, 5, baselineOf(h), dim(p.text, active, p), "left");
  if (marked) {
    setColor(dim(p.read, active, p));
    mgraphics.ellipse(Math.round(5 + measure(shown) + 4), Math.round(h / 2) - 2, 4, 4);
    mgraphics.fill();
  }
  setColor(dim(p.label, active, p));
  mgraphics.move_to(w - 11, h / 2 - 2);
  mgraphics.line_to(w - 4, h / 2 - 2);
  mgraphics.line_to(w - 7.5, h / 2 + 2);
  mgraphics.close_path();
  mgraphics.fill();
}
