#!/usr/bin/env python3
"""gencheck - static checker for gen~ codebox text (GenExpr).

Finds patterns that made Max refuse to compile, crash, or go silent in real use.
Passing this check is NOT a compile check. Only Max can compile GenExpr.
Rules and evidence: the max-gen-helper plugin (README.md, skills/gen-pitfalls/references) and maxprobe/ next to
this file (every Max probe codebox and its result).

usage: gencheck.py [options] FILE...
  FILE is codebox text (.txt, .genexpr) or a Max patcher (.maxpat, .gendsp, .maxhelp): then each gen~ codebox in it
  is checked on its own (jit.gen, jit.pix and RNBO codeboxes are skipped)
  --old OLD        older version of the same codebox (finds new names that collide, G302)
  --io NIN NOUT    expected inlet/outlet counts of the gen~ (G504)
  --strict         warnings also make exit code 1
  --info           list info findings (default: count only)
  --json           print findings as JSON
  --gen-ref DIR    Gen refpages folder (default: search the Max install, or $GENCHECK_GEN_REF)
  --max-version V  judge as Max version V. Default: the Max the user started last (read from the version line at the
                   top of Max's own log files; $GENCHECK_MAX_LOGS sets other log folders, empty = do not read them),
                   else the version of the Max install found, else the 9.2.0 rules. The first output line says which
  --gen-path DIR   extra folder (searched with its subfolders) with gen abstractions (*.gendsp) and require()
                   libraries (*.genexpr); the folder of each checked file is always searched, and require()
                   libraries are also looked up in Max's packages, Examples and Library folders
  --param NAME     NAME is a param of the gen patcher (an object box [param NAME ...]); the codebox may read it
                   without a declaration. Repeat for each one
  --complete-params  the --param names are every [param], [history], [data] and [buffer] box of the gen patcher:
                   another undeclared name the code reads is then an error ('variable X is not defined'). A Param
                   declared in another codebox of the same gen patcher is a param too: for codebox text pass it with
                   --param; for a patcher file gencheck adds those itself
  --max-per-rule N show at most N lines per rule per file (default 5, 0 = all)
  --write-gendsp OUT.gendsp  with one codebox text file and no error: also write it as a gen patcher file (one
                   codebox wired to in/out boxes) to use as [gen~ @gen OUT]. A file gencheck did not write is kept
  --log FILE       append one line per run to a local log: Max version, rule IDs and counts (no code, no file
                   names). Nothing is ever sent by gencheck
  --log-mismatch TEXT  with --log and one file: record that Max did something else (TEXT = what Max printed)
  --log-code       with --log-mismatch: keep the code too (only with the user's consent)
  --log-summary    with --log: count the reports and print a draft issue for the ones not sent yet
  --log-mark-sent  with --log: mark those reports as sent (after the user submitted the issue)
exit: 0 ok, 1 error found (or warn with --strict), 2 usage problem or a file that cannot be read, 3 gencheck itself
  failed on a file. With several files the highest code wins; the other files are still checked
Python 3 standard library only.
"""
import sys, os, re, glob, json, math, threading, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import genflow  # noqa: E402

VERSION = "0.1.2"
ISSUE_REPO = "mforhm/max-gen-helper"   # the public repository: --log-summary prints an issue link to it

# ----------------------------------------------------------------- rules

RULES = {
    "G100": ("error", "cannot parse"),
    "G400": ("info", "flow analysis skipped a statement (warn: an analysis failed, please report it)"),
    "G101": ("error", "declaration after an expression"),
    "G102": ("error", "variable first assigned inside a block, read after it (value not constant, or both if/else "
                      "branches)"),
    "G103": ("error", "read before it is first assigned, and the value is used"),
    "G126": ("warn", "variable first assigned inside a block: after it, it always holds that constant"),
    "G127": ("info", "more names than values in 'a, b = x': the extra names get 0"),
    "G128": ("info", "output assigned only inside an if: 0 where that code does not run"),
    "G129": ("error", "'name.member' without () (jit.gen swizzle syntax) on a name that is not a Data, Buffer or Delay"),
    "G130": ("error", "Max 9.1.x: a user function with a branch (a ?: return, a return inside an if block, or a returned "
                      "variable that an if block sets) is called inside a poke/write value (info on 9.2)"),
    "G131": ("error", "Max 9.1.x: an output outN is not assigned in the main code (info on 9.2)"),
    "G132": ("error", "Max 9.1.x: empty for loop body (info on 9.2)"),
    "G133": ("error", "Max 9.1.x: a function that comes from a nested require (info on 9.2)"),
    "G134": ("error", "a '+' that is not a binary operator: unary plus (+x), or a plus sign in an exponent (1e+3)"),
    "G104": ("warn", "name is not defined in this codebox"),
    "G105": ("warn", "unknown function"),
    "G108": ("error", "gen operator used without ()"),
    "G109": ("error", "graphical gen object called as a function"),
    "G111": ("error", "user function defined after a statement or declaration"),
    "G110": ("info", "uses a data/buffer object from the gen patcher"),
    "G112": ("error", "assignment to a predefined constant name (Max 9.2.0)"),
    "G113": ("warn", "unknown Param attribute"),
    "G114": ("error", "called user function without a return value (no return, or only 'return;')"),
    "G115": ("error", "Buffer name not in quotes"),
    "G116": ("info", "require(...) without ';'"),
    "G117": ("error", "require()'d library not found"),
    "G118": ("error", "require() not at the top of the codebox"),
    "G119": ("error", "declaration keyword in lower case"),
    "G120": ("error", "assignment to an inlet (in1, in2, ...)"),
    "G121": ("error", "assignment to a Param"),
    "G122": ("info", "expression statement whose value is not used"),
    "G123": ("warn", "a require()'d library does not parse or cannot be read (what Max does then was not measured)"),
    "G124": ("warn", "syntax form not confirmed in Max"),
    "G125": ("error", "upper-case form of a Gen global (VOICE, ELAPSED)"),
    "G106": ("info", "more arguments than the Gen reference lists"),
    "G107": ("warn", "unknown method"),
    "G201": ("info", "user function call inside a user function's arguments"),
    "G202": ("info", "user function called inside an if/for/while block"),
    "G203": ("info", "user function parameter/local has the same name as a main-body name"),
    "G204": ("info", "user function calls another user function"),
    "G205": ("error", "user function reads a name it cannot see (main-code variable, History, Param, Data, inlet)"),
    "G206": ("warn", "user function named like a gen operator: the built-in runs ('pass' fails)"),
    "G207": ("info", "local function replaces a require()'d library function of the same name"),
    "G208": ("warn", "user function called with fewer or more arguments than it has parameters"),
    "G209": ("warn", "user function defined more than once"),
    "G210": ("warn", "a user function that writes is called, but its result is never used: Max drops the call and its "
                     "writes"),
    "G301": ("warn", "declared twice"),
    "G302": ("warn", "new declaration reuses a name from the old version"),
    "G303": ("info", "name is also a gen operator"),
    "G304": ("info", "name differs from a gen operator only by case"),
    "G401": ("warn", "interpolated buffer read without clamp on the index"),
    "G402": ("info", "peek without boundmode"),
    "G403": ("warn", "fract() hash dice can be negative"),
    "G404": ("info", "fract() keeps the sign of negative input"),
    "G405": ("warn", "noise() is already -1..1"),
    "G406": ("warn", "mc_channel()"),
    "G407": ("info", "Param without min/max and a default outside 0..1 (Max keeps it; exported code clips it)"),
    "G408": ("warn", "Delay read longer than the Delay"),
    "G412": ("info", "Param without min/max (0..1 range)"),
    "G413": ("warn", "built-in attribute set from a variable, from a word without quotes, or to a value it does not have"),
    "G414": ("info", "Param initial value outside its min/max (Max clamps it)"),
    "G416": ("warn", "name = value argument that is not an attribute of the operator (or a parameter of the user function)"),
    "G415": ("warn", "codebox Param with the same name as a gen-patcher param (--param): the patcher value wins"),
    "G410": ("info", "feedback-like Param max is close to 1"),
    "G411": ("info", "hard-coded sample rate"),
    "G501": ("info", "heavy functions inside ?: (both sides are computed)"),
    "G502": ("info", "codebox file is large (150 KB of plain statements ran: probe R1250)"),
    "G503": ("info", "non-ASCII characters"),
    "G505": ("warn", "code nested too deeply for gencheck: not checked"),
    "G506": ("warn", "the file starts with a byte order mark (BOM)"),
    "G504": ("warn", "inlet/outlet count differs from --io"),
}

DECL_KW = ("History", "Param", "Data", "Delay", "Buffer")
LOWER_DECL = {k.lower(): k for k in DECL_KW}   # 'param x(0);' parses but fails (probes R231, R461, R980-R982)
LOWER_DECL_PROBE = {"param": "R231", "history": "R461", "data": "R980", "buffer": "R981", "delay": "R982"}
STMT_KW = {"if", "else", "for", "while", "return", "break", "continue"} | set(DECL_KW)
ASSIGN_OPS = ("=", "+=", "-=", "*=", "/=", "%=")
# gen objects that exist as patcher objects but are declared, not called, in GenExpr
# history(x) fails at audio start: "use of undeclared identifier 'history'" (round 6, P-12). The others: not tested
NOT_CALLABLE = {"history": "History", "delay": "Delay", "data": "Data", "buffer": "Buffer", "param": "Param",
                "in": "inN", "out": "outN"}
TESTED_NOT_CALLABLE = {"history"}
# Names measured in Max 9.2.0 with audio on. Used with or without the local Gen reference, so these checks
# also work where the Max install is not found (the reference itself is never copied into gencheck).
MEASURED_CONSTANTS = {"pi", "twopi", "halfpi", "invpi", "degtorad", "radtodeg", "ln2", "ln10", "log2e", "log10e",
                      "sqrt2", "sqrt1_2", "phi", "e", "samplerate", "vectorsize", "fftsize", "ffthop", "fftoffset",
                      "fftfullspect"}  # assignment refused, also upper case (rounds 5, 9, 10)
GLOBALS = {"elapsed", "voice", "voicecount", "mc_channel", "mc_channelcount"}  # read without (); voice, mc_channel assignable
# user functions named like gen operators: Max ignores them and runs the built-in; 'pass' fails (round 11-13)
MEASURED_OP_FUNCS = {"scale": "R447, R622, R1053", "mix": "R820", "cycle": "R822", "wrap": "R1233", "pass": "R821"}
# Names of the callable Gen operators (names only), used when the local Gen reference is not found: a user function
# with one of these names may be replaced by the operator (probes R622, R820, R822), so errors in its body only warn
FALLBACK_OPS = set("""
    abs absdiff accum acos acosh add and asin asinh atan atan2 atanh atodb bool cartopol ceil change channels clamp
    clip cos cosh counter cycle dbtoa dcblock degrees delta dim div eq eqp exp exp2 expr fastcos fastexp fastpow
    fastsin fasttan fftinfo fixdenorm fixnan floor fold fract ftom gate gen gt gte gtep gtp hypot interp isdenorm
    isnan latch ln log log10 log2 lookup lt lte ltep ltp max maximum min minimum mix mod mstosamps mtof mul
    mulequals nearest neg neq neqp noise not or pass peek phasewrap phasor plusequals poke poltocar pow radians
    rate rdiv receive rmod round rsub sah sample sampstoms scale selector send setparam sign sin sinh slide
    smoothstep splat sqrt step sub switch t60 t60time tan tanh train triangle trunc wave wrap xor
""".split())
MEASURED_BARE_FAIL = {"noise"}  # used without (): 'variable noise is not defined' (P-11)
INTERP_READERS = {"peek": "none", "sample": "linear", "wave": "linear", "lookup": "linear"}
ATTR_OPS = set(INTERP_READERS) | {"poke", "nearest", "cycle"}   # built-ins with attributes, used without the reference
HEAVY = {"pow", "exp", "exp2", "log", "log2", "log10", "ln", "sin", "cos", "tan", "tanh",
         "sinh", "cosh", "atan", "atan2", "asin", "acos", "sqrt", "fastpow", "fastexp"}
KNOWN_METHODS = {"Delay": {"read", "write"},
                 "Data": {"peek", "poke", "sample", "lookup", "wave", "nearest", "dim", "channels", "read", "write"},
                 "Buffer": {"peek", "poke", "sample", "lookup", "wave", "nearest", "dim", "channels", "read", "write"}}
BIG_FILE = 100000
BUFFER_FUNCS = {"peek", "poke", "sample", "lookup", "wave", "nearest", "dim", "channels", "splat"}
# bare names that compile without a declaration (Cycling '74 examples: TWOPI, PI, SQRT2, e; gen.maxhelp: out = i)
EXTRA_BARE = {"e", "E", "in", "out"}
# ----------------------------------------------------------------- Gen reference


def install_version(res):
    """CFBundleShortVersionString of the Max.app whose Resources folder is res (macOS), or None"""
    try:
        import plistlib
        with open(os.path.join(os.path.dirname(res), "Info.plist"), "rb") as f:
            return plistlib.load(f).get("CFBundleShortVersionString", "").split(" ")[0] or None
    except Exception:
        return None


def find_ref(explicit=None, prefer=None):
    """the Gen refpages folder: --gen-ref, $GENCHECK_GEN_REF, else the Max install of version `prefer` if there is
    one, else the first Max install found"""
    cands = []
    if explicit:
        cands.append(explicit)
    if os.environ.get("GENCHECK_GEN_REF"):
        cands.append(os.environ["GENCHECK_GEN_REF"])
    apps = max_app_resources()
    if prefer:
        apps = [r for r in apps if install_version(r) == prefer] + [r for r in apps if install_version(r) != prefer]
    for res in apps:
        cands += [os.path.join(res, "C74", "packages", "Gen", "docs", "refpages"),
                  os.path.join(res, "packages", "Gen", "docs", "refpages")]
    for c in cands:
        if os.path.isdir(os.path.join(c, "common")) and os.path.isdir(os.path.join(c, "dsp")):
            return c
    return None


MAX_START_RE = re.compile(r"^\[(\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d)[^\]]*\].*?Max is starting: Version (\d+\.\d+(?:\.\d+)?)",
                          re.M)


def max_log_dirs():
    """folders of Max's own log files. $GENCHECK_MAX_LOGS (folders joined by os.pathsep; empty = do not read logs)
    replaces them. macOS: seen on Max 9.1.4 and 9.2.0. Windows: a guess, not checked"""
    env = os.environ.get("GENCHECK_MAX_LOGS")
    if env is not None:
        return [d for d in env.split(os.pathsep) if d]
    roots = [os.path.expanduser("~/Library/Application Support/Cycling '74")]
    if os.environ.get("APPDATA"):
        roots.append(os.path.join(os.environ["APPDATA"], "Cycling '74"))
    return [d for r in roots for d in sorted(glob.glob(os.path.join(glob.escape(r), "Max *", "Logs")))]


def last_started_max():
    """(version, start time) of the Max that started last, or None. Each start of Max writes
    'Max is starting: Version 9.1.4 (...)' at the top of a new Max.log (Max) or MaxPlugLib.log (Max for Live inside
    Live); older starts move to Max.1.log, Max.2.log ... Only that line is used; nothing else of the log is kept"""
    best = None
    for d in max_log_dirs():
        for p in glob.glob(os.path.join(glob.escape(d), "Max*.log")):
            try:
                with open(p, encoding="utf-8", errors="replace") as f:
                    m = MAX_START_RE.search(f.read(8192))
            except OSError:
                continue
            if m:
                when = m.group(1).replace("T", " ")
                if best is None or when > best[1]:
                    best = (m.group(2), when)
    return best


class GenRef:
    """Operator names, categories and max argument counts, read from the user's own Max install."""

    def __init__(self, path):
        self.path = path
        self.ops = {}
        if not path:
            return
        for f in glob.glob(os.path.join(path, "dsp", "*.maxref.xml")) + glob.glob(os.path.join(path, "common", "*.maxref.xml")):
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    s = fh.read()
            except OSError:
                continue                   # an unreadable refpage: that operator is unknown, the rest still works
            m = re.search(r"<c74object name='([^']+)'", s)
            if not m:
                continue
            cat = re.search(r"category='([^']*)'", s)
            maxargs, found = 0, False
            for a, i in re.findall(r"\{ arguments=\{([^}]*)\}, inlets=\{([^}]*)\} \}", s):
                found = True
                if "..." in a or "..." in i:
                    maxargs = None
                    break
                n = len([x for x in a.split(",") if x.strip()]) + len([x for x in i.split(",") if x.strip()])
                maxargs = max(maxargs, n)
            attrs = {}                     # attribute -> its enum values ([] if not an enum)
            for a in re.finditer(r"<attribute name='(\w+)' type='\w+' get='0' set='1'>(.*?)(?=<attribute name='\w+' "
                                 r"type='\w+' get='0' set='1'>|</c74object>)", s, re.S):
                attrs[a.group(1)] = re.findall(r"<enum name='([^']+)'>", a.group(2))
            self.ops[m.group(1)] = {"cat": cat.group(1) if cat else "", "maxargs": maxargs if found else None,
                                    "attrs": attrs}

    def __bool__(self):
        return bool(self.ops)

    def max_version(self):
        """CFBundleShortVersionString of the Max.app that holds these refpages, or None"""
        d = self.path
        for _ in range(10):
            if not d:
                return None
            plist = os.path.join(d, "Info.plist")
            if os.path.basename(d) == "Contents" and os.path.isfile(plist):
                try:
                    import plistlib
                    with open(plist, "rb") as f:
                        return plistlib.load(f).get("CFBundleShortVersionString", "").split(" ")[0] or None
                except Exception:
                    return None
            d = os.path.dirname(d)
        return None

    def constant(self, name):
        """names Max 9.2.0 refuses as assignment targets (round 5: pi, twopi, samplerate, e, phi, PHI;
        voice and mc_channel were accepted)"""
        if name == "e":
            return True
        o = self.ops.get(name)
        return bool(o) and o["cat"] == "constant" and name not in ("int", "float", "constant")

    def bare_ok(self, name):
        o = self.ops.get(name)
        return bool(o) and o["cat"] in ("constant", "global")

    def callable(self, name):
        """a Gen operator that GenExpr code calls as name(...). read and write (category 'nil') are only Delay methods:
        a user function named read is a normal user function (probe R1234)"""
        return name in self.ops and name not in NOT_CALLABLE and self.ops[name]["cat"] != "nil"


# ----------------------------------------------------------------- tokens

TOKEN_RE = re.compile(r"""
 (?P<ws>[ \t\r\f\v]+) | (?P<nl>\n) |
 (?P<lc>//[^\n]*) | (?P<bc>/\*.*?\*/) | (?P<bco>/\*) |
 (?P<str>"[^"\n]*") | (?P<mstr>"[^"]*") | (?P<sq>') |
 (?P<num>0[xX][0-9A-Fa-f]+|(?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)(?:[eE][+-]?[0-9]+)?) |
 (?P<id>[^\W\d]\w*) |
 (?P<op>\^\^|\+\+|==|!=|<=|>=|&&|\|\||\+=|-=|\*=|/=|%=|<<|>>|[-+*/%<>=!?:;,(){}\[\].&|^~]) |
 (?P<bad>.)""", re.X | re.S)


class Tok:
    __slots__ = ("kind", "text", "line")

    def __init__(self, kind, text, line):
        self.kind, self.text, self.line = kind, text, line

    def __repr__(self):
        return "%s:%r@%d" % (self.kind, self.text, self.line)


class ParseError(Exception):
    def __init__(self, line, msg):
        Exception.__init__(self, msg)
        self.line = line


# characters measured in Max 9.2.0: the codebox fails at load and no message names the character
MEASURED_CHARS = {"\u00a0": "R235, R501, R861", "\u200b": "R236, R503, R863", "\u201c": "R505, R865",
                  "\u201d": "R505, R865", "\ufeff": "R507, R687, R867"}
CHAR_FIX = {"Zs": "Retype it as a normal space", "Zl": "Retype it as a line break", "Zp": "Retype it as a line break",
            "Cf": "Delete it", "Pi": "Retype it as a straight quote", "Pf": "Retype it as a straight quote",
            "Pd": "Retype it as '-'"}


def bad_char(ch, line, col):
    """message for a character outside comments that GenExpr cannot read"""
    if ch == '"':
        return "unterminated string: '\"' without its closing '\"' on the same line"
    o = ord(ch)
    if o < 128:
        return "invalid character %r at line %d" % (ch, line) + (" (comments start with //)" if ch == "#" else "")
    name = unicodedata.name(ch, "")
    cat = unicodedata.category(ch)
    what = "U+%04X%s" % (o, " (%s)" % name if name else "")
    fix = CHAR_FIX.get(cat, "Retype it as %s" % {"\u2212": "'-'", "\u00d7": "'*'", "\u00f7": "'/'"}.get(ch, "plain ASCII"))
    if ch == "\ufeff" and line == 1 and col == 1:
        fix = "It is a byte order mark (BOM) at the start of the code: delete it"
    if ch in MEASURED_CHARS:
        why = "Max refuses the codebox at load and does not name the character (probes %s)" % MEASURED_CHARS[ch]
    else:
        why = ("Max refused every invisible or typographic character tested outside comments, at load and without "
               "naming it (probes R501, R503, R505, R507)")
    return "%s at line %d, column %d, outside a comment. %s. %s" % (what, line, col, why, fix)


SINGLE_QUOTE = "single quotes are not GenExpr: write \"name\". Max: invalid character: ' (probe R234)"


def tokenize(src, notes=None):
    """tokens of GenExpr code. notes (a list) receives warnings that do not stop the parse"""
    toks, line, line_start = [], 1, 0
    for m in TOKEN_RE.finditer(src):
        k, t = m.lastgroup, m.group()
        if k == "nl":
            line += 1
            line_start = m.end()
        elif k in ("ws", "lc"):
            pass
        elif k == "bc":
            if "\n" in t:
                line += t.count("\n")
                line_start = m.start() + t.rfind("\n") + 1
        elif k == "bco":
            raise ParseError(line, "this /* comment is never closed. Max refuses the codebox at load: 'unfinished "
                                   "comment' (Max 9.2.0; Max 9.1.4 refuses it too, probe R1120). Close it with */")
        elif k == "mstr":
            raise ParseError(line, "this string runs over %d line break(s). Max refuses the codebox at load: 'string "
                                   "missing closing \"' (Max 9.2.0; Max 9.1.4 refuses it too, probe R1122). Put the "
                                   "string on one line" % t.count("\n"))
        elif k == "sq":
            raise ParseError(line, SINGLE_QUOTE)
        elif k == "bad":
            raise ParseError(line, bad_char(t, line, m.start() - line_start + 1))
        else:
            if k == "id" and not t.isascii():
                bad = next(ch for ch in t if ord(ch) > 127)
                raise ParseError(line, "non-ASCII letter %r (U+%04X) in the name '%s'. Max 9.1.4 and 9.2.0 refuse the "
                                       "codebox (probe R1004; inside a quoted Buffer name it is fine, probe R1005). Use "
                                       "ASCII letters, digits and _ in names" % (bad, ord(bad), t))
            toks.append(Tok(k, t, line))
    return toks


# ----------------------------------------------------------------- expressions


def match_close(toks, i):
    """toks[i] is ( or [ ; return index of the matching close."""
    pairs = {"(": ")", "[": "]"}
    stack = []
    for j in range(i, len(toks)):
        t = toks[j].text
        if t in pairs:
            stack.append(pairs[t])
        elif t in (")", "]"):
            if not stack or stack.pop() != t:
                raise ParseError(toks[j].line, "unbalanced %r" % t)
            if not stack:
                return j
    raise ParseError(toks[i].line, "unclosed %r" % toks[i].text)


def split_commas(toks):
    parts, cur, depth = [], [], 0
    for t in toks:
        if t.text in ("(", "["):
            depth += 1
        elif t.text in (")", "]"):
            depth -= 1
        if t.text == "," and depth == 0:
            parts.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur or parts:
        parts.append(cur)
    return parts


BINARY_OPS = {"+", "-", "*", "/", "%", "<", ">", "<=", ">=", "==", "!=", "&&", "||", "^^"}  # ^^ is xor (probe R969)
UNARY_OPS = {"-", "+", "!"}
NOT_OPERATORS = {
    "<<": "'<<' is not a GenExpr operator (no bit shifts). Max: statement missing ';' (probes R476, R689)",
    ">>": "'>>' is not a GenExpr operator (no bit shifts; '<<' fails in Max: statement missing ';', probes R476, R689)",
    "&": "'&' is not a GenExpr operator; for logical and write &&. Max: statement missing ';' (probe R477)",
    "|": "'|' is not a GenExpr operator; for logical or write ||. Max: statement missing ';' (probe R478)",
    "^": "'^' is not a GenExpr operator: for a power write pow(x, y), for xor write ^^. Max: statement missing ';' "
         "(probes R480, R691)",
    "~": "'~' is not a GenExpr operator (no bitwise operators; & | ^ << fail in Max, probes R476-R478, R480)",
}
INC_DEC = "GenExpr has no '%s' operator: write x += 1 or x -= 1. Max: statement missing ';' (probe R230)"
# '--' is not a token: Max reads 3--1 as 3 - (-1) = 4 on 9.1.4 and 9.2.0 (probe R1002), so x-- ends with a minus
DEC = ("GenExpr has no '--' operator: Max reads it as two minus signs (3--1 is 4, probe R1002), so '%s--' is missing a "
       "value ('%s++' fails: statement missing ';', probe R230). Write %s -= 1")
NO_BRACKETS = "GenExpr has no [ ] (no arrays or indexing). Max: statement missing ';' (probe R961). Use a Data or Buffer " \
              "with peek() / poke()"


def missing_semicolon(line, probe="R188"):
    return "missing ';' at the end of line %d. Max: statement missing ';' (probe%s %s)" % (line, "s" if "," in probe else "",
                                                                                            probe)


def _operand_error(toks, i):
    t = toks[i]
    x = t.text
    if x == "++":
        return INC_DEC % x
    if x in NOT_OPERATORS:
        return NOT_OPERATORS[x]
    if x == "[":
        return NO_BRACKETS
    if t.kind == "id":
        return "unexpected '%s' inside an expression" % x
    if i == 0:
        return "expression starts with %r" % x
    return "missing value between %r and %r" % (toks[i - 1].text, x)


def _operator_error(toks, i, ctx, frames):
    t, prev = toks[i], toks[i - 1]
    x = t.text
    if t.kind in ("id", "num", "str") or x == "(":
        if t.line > prev.line:
            return missing_semicolon(prev.line)
        return "missing operator between %r and %r. Max: statement missing ';'" % (prev.text, x)
    if x == "++":
        return INC_DEC % x
    if x in NOT_OPERATORS:
        return NOT_OPERATORS[x]
    if x == "[":
        return NO_BRACKETS
    if x in ASSIGN_OPS:
        if ctx == "rhs" and len(frames) == 1 and prev.kind == "id":
            return ("chained assignment ('a = b = x') is not allowed. Max: statement missing ';' (probes R467, R695). "
                    "Write b = x; a = b;")
        if ctx == "cond":
            return ("'%s' inside a condition: GenExpr has no assignment inside expressions. Max: function call missing "
                    "'(' (probe R232). For a comparison write ==" % x)
        if ctx == "stmt" and len(frames) == 1:
            return "'%s' needs a plain variable name on its left" % x
        return "'%s' inside an expression: GenExpr has no assignment inside expressions (probes R232, R467)" % x
    return "unexpected %r after %r" % (x, prev.text)


def check_expr(toks, ctx, line=0):
    """Raise ParseError unless toks is a GenExpr expression (or a comma list of expressions).
    ctx: 'rhs' (right side of an assignment), 'stmt' (expression statement), 'cond', 'return', 'args'.
    Operands and binary operators must alternate; ( ), calls and ?: must pair up. Loops instead of recursion, so
    very long or deep expressions are fine."""
    if not toks:
        raise ParseError(line, "missing expression")
    frames = [["top", 0, ctx == "args"]]   # [kind, open '?', at the start of a call argument]
    want_operand = True
    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        x = t.text
        top = frames[-1]
        if want_operand:
            arg_start, top[2] = top[2], False
            if t.kind == "str" and not any(f[0] == "call" for f in frames):
                raise ParseError(t.line, "the string %s is used as a value. Max 9.1.4 and 9.2.0 refuse the codebox "
                                         "(probe R1208). Strings are only for Buffer names, attribute values and "
                                         "require(); use a number" % short(x, 30))
            if t.kind in ("num", "str"):
                want_operand = False
            elif t.kind == "id":
                if x in STMT_KW:
                    raise ParseError(t.line, _operand_error(toks, i))
                nx = toks[i + 1].text if i + 1 < n else None
                if arg_start and nx == "=" and top[0] in ("call", "top"):
                    i += 2                     # named argument: name = value
                    continue
                if nx == "(":
                    frames.append(["call", 0, True])
                    i += 2
                    continue
                want_operand = False
            elif x == "(":
                frames.append(["group", 0, False, i])
            elif x in UNARY_OPS:
                pass
            elif x == ")" and top[0] == "call" and i > 0 and toks[i - 1].text == "(":
                frames.pop()                   # f()
                want_operand = False
            else:
                raise ParseError(t.line, _operand_error(toks, i))
        else:
            if x in BINARY_OPS:
                want_operand = True
            elif x == "?":
                top[1] += 1
                want_operand = True
            elif x == ":" and top[1]:
                top[1] -= 1
                want_operand = True
            elif x == ")" and top[0] != "top" and not top[1]:
                frames.pop()
            elif x == "," and not top[1] and top[0] == "group":
                try:
                    group = short(pretty(Expr(toks[top[3]:match_close(toks, top[3]) + 1])), 40)
                except ParseError:
                    group = "(..., ...)"
                raise ParseError(t.line, "',' inside ( ) that is not a function call: %s is not a GenExpr value. Max "
                                         "9.1.4 and 9.2.0 refuse the codebox ((1, 2): probe R1011). A ',' separates "
                                         "call arguments, or the values of 'a, b = x, y' and 'return x, y'" % group)
            elif x == "," and not top[1]:
                top[2] = top[0] == "call"
                want_operand = True
            elif x == "." and i + 1 < n and toks[i + 1].kind == "id":
                if i + 2 < n and toks[i + 2].text == "(":
                    frames.append(["call", 0, True])     # obj.method(...)
                    want_operand = True
                    i += 3
                else:
                    i += 2                               # obj.member
                continue
            elif x in (":", ")", ","):
                raise ParseError(t.line, "'?' without ':'" if top[1] else ("':' without '?'" if x == ":" else
                                                                             "unbalanced %r" % x))
            else:
                newline = t.line > toks[i - 1].line and (t.kind in ("id", "num", "str") or x == "(")
                raise ParseError(toks[i - 1].line if newline else t.line, _operator_error(toks, i, ctx, frames))
        i += 1
    if want_operand:
        if n >= 2 and toks[-1].text == "-" and toks[-2].text == "-":
            x = toks[-3].text if n >= 3 and toks[-3].kind == "id" else "x"
            raise ParseError(toks[-1].line, DEC % (x, x, x))
        raise ParseError(toks[-1].line, "the expression ends with %r: a value is missing after it" % toks[-1].text)
    if len(frames) > 1:
        raise ParseError(toks[-1].line, "unclosed '('")
    if frames[0][1]:
        raise ParseError(toks[-1].line, "'?' without ':'")


def check_call_args(name_tok, inner):
    """arguments of a declaration or call: name(inner)"""
    check_expr([name_tok, Tok("op", "(", name_tok.line)] + list(inner) + [Tok("op", ")", name_tok.line)], "rhs")


class Call:
    __slots__ = ("name", "obj", "line", "args", "named", "start", "end")

    def __init__(self, name, obj, line, args, named):
        self.name, self.obj, self.line, self.args, self.named = name, obj, line, args, named
        self.start = self.end = None


class Expr:
    def __init__(self, toks):
        self.toks = toks
        self.calls, self.reads, self.members = [], [], []
        i, n = 0, len(toks)
        while i < n:
            t = toks[i]
            if t.text in ("{", "}", ";"):
                raise ParseError(t.line, "unexpected %r inside an expression" % t.text)
            if t.kind != "id":
                i += 1
                continue
            nx = toks[i + 1].text if i + 1 < n else None
            if nx == "." and i + 3 < n and toks[i + 2].kind == "id" and toks[i + 3].text == "(":
                j = match_close(toks, i + 3)
                self.reads.append((t.text, t.line))
                c = self._call(toks[i + 2].text, t.text, t.line, toks[i + 4:j])
                c.start, c.end = i, j
                self.calls.append(c)
                i = j + 1
                continue
            if nx == "." and i + 2 < n and toks[i + 2].kind == "id":
                self.reads.append((t.text, t.line))       # obj.member without (): a jit.gen swizzle, or d.dim (R350)
                self.members.append((t.text, toks[i + 2].text, t.line))
                i += 3
                continue
            if nx == "(":
                j = match_close(toks, i + 1)
                c = self._call(t.text, None, t.line, toks[i + 2:j])
                c.start, c.end = i, j
                self.calls.append(c)
                i = j + 1
                continue
            self.reads.append((t.text, t.line))
            i += 1

    @staticmethod
    def _call(name, obj, line, inner):
        args, named = [], {}
        for part in split_commas(inner):
            if not part:
                raise ParseError(line, "empty argument in %s()" % name)
            if len(part) >= 2 and part[0].kind == "id" and part[1].text == "=":
                named[part[0].text] = Expr(part[2:])
            else:
                args.append(Expr(part))
        return Call(name, obj, line, args, named)

    def all_calls(self):
        out = []
        for c in self.calls:
            out.append(c)
            for a in c.args + list(c.named.values()):
                out += a.all_calls()
        return out

    def all_reads(self):
        out = list(self.reads)
        for c in self.calls:
            for a in c.args + list(c.named.values()):
                out += a.all_reads()
        return out

    def all_members(self):
        out = list(self.members)
        for c in self.calls:
            for a in c.args + list(c.named.values()):
                out += a.all_members()
        return out

    def text(self):
        return " ".join(t.text for t in self.toks)


# ----------------------------------------------------------------- statements

class Node:
    def __init__(self, kind, line, **kw):
        self.kind, self.line = kind, line
        self.__dict__.update(kw)


class Parser:
    def __init__(self, toks):
        self.t, self.p = toks, 0
        self.open_end = None     # line of a last statement that has no ';'
        self.notes = []          # non-error findings of the parser
        self.in_func = False     # inside a function body: return is allowed (probe R1205)
        self.loops = 0           # for / while bodies around this statement: break / continue allowed (probe R1206)

    def peek(self, k=0):
        j = self.p + k
        return self.t[j] if j < len(self.t) else None

    def text(self, k=0):
        t = self.peek(k)
        return t.text if t else None

    def line(self):
        t = self.peek()
        return t.line if t else (self.t[-1].line if self.t else 1)

    def take(self, want=None):
        t = self.peek()
        if t is None:
            raise ParseError(self.line(), "unexpected end of code" + (", expected %r" % want if want else ""))
        if want is not None and t.text != want:
            raise ParseError(t.line, "expected %r, found %r" % (want, t.text))
        self.p += 1
        return t

    def until(self, kind="stmt"):
        """tokens of one statement up to its ';' (not consumed). At the end of the code without ';' it returns
        the tokens and records the line in self.open_end (program() decides: only a codebox that is a single
        statement may leave the ';' out, probe R950). '{', '}' or a keyword inside a statement: a ';' is missing"""
        out, depth = [], 0
        while True:
            t = self.peek()
            if t is None:
                if depth == 0 and out:
                    self.open_end = out[-1].line
                    return out
                raise ParseError(self.line(), "unclosed '('" if depth else "unexpected end of code")
            x = t.text
            if depth == 0 and x == ";":
                return out
            if x == ";":
                raise ParseError(t.line, "unclosed '(' before ';'")
            if out and (x in ("{", "}") or (depth == 0 and t.kind == "id" and x in STMT_KW)):
                self.missing_semi(out, kind, t)
            if x in ("(", "["):
                depth += 1
            elif x in (")", "]"):
                depth -= 1
                if depth < 0:
                    raise ParseError(t.line, "unbalanced %r" % x)
            elif x in ("{", "}"):
                raise ParseError(t.line, "unexpected %r" % x)
            out.append(t)
            self.p += 1

    @staticmethod
    def missing_semi(out, kind, stop):
        """a statement ran into '{', '}' or a keyword: say where its ';' is missing"""
        if kind == "return":
            check_expr(out, "return")
            raise ParseError(out[-1].line, "missing ';' after return (line %d). Max: jump statement missing ';' "
                                           "(probe R186)" % out[-1].line)
        simple(out, out[0].line)           # two statements without ';' between them are found here (probe R188)
        if stop.text == "}":
            raise ParseError(out[-1].line, "missing ';' at the end of line %d, before '}'. Max: statement missing ';' "
                                           "(probe R185)" % out[-1].line)
        raise ParseError(out[-1].line, missing_semicolon(out[-1].line))

    def program(self):
        items = []
        while self.peek() is not None:
            if self.is_require():
                items.append(self.require())
            elif self.is_funcdef():
                items.append(self.funcdef())
            else:
                items.append(self.stmt())
        if self.open_end is not None:
            stmts = [n for n in items if n.kind not in ("func", "decl") and not is_require(n)]
            end = self.open_end
            if len(items) == 1 and items[0].kind in ("assign", "expr"):
                items[0].implicit = True   # a codebox that is one statement needs no ';' (probes R950, R952)
            elif len(stmts) >= 2:
                raise ParseError(end, "missing ';' at the end of line %d (the last statement). Max: statement missing "
                                      "';' (probe R187). Only a codebox that is one plain statement (out1 = in1 or "
                                      "cos(in1)) may leave it out (probes R950, R952). Add ';'" % end)
            elif (len(stmts) == 1 and stmts[0].kind in ("assign", "expr")
                  and any(n.kind in ("func", "decl") for n in items)):
                raise ParseError(end, "missing ';' at the end of line %d (the last statement). After a %s, one "
                                      "statement without ';' is refused by Max 9.1.4 and 9.2.0 (%s); only a "
                                      "codebox that is one plain statement may leave it out (probes R950, R952). Add "
                                      "';'" % (end, "function" if any(n.kind == "func" for n in items) else
                                               "declaration", "probe R1007" if any(n.kind == "func" for n in items)
                                               else "probes R1200, R1201"))
            elif len(items) == 1 and items[0].kind == "if" and items[0].els is None:
                raise ParseError(end, "missing ';' at the end of line %d. A codebox that is one if without braces "
                                      "and without ';' is refused by Max 9.1.4 and 9.2.0 (probe R1008); only one plain "
                                      "statement may leave it out (probes R950, R952). Add ';'" % end)
            elif ((len(items) == 1 and items[0].kind == "for") or
                  (len(items) == 1 and items[0].kind == "if" and items[0].els is not None) or
                  (len(stmts) == 1 and stmts[0].kind in ("assign", "expr") and any(is_require(n) for n in items))):
                what = ("one for statement" if items[0].kind == "for" else "one if/else"
                        if items[0].kind == "if" else "a require and one statement")
                raise ParseError(end, "missing ';' at the end of line %d. A codebox that is %s without the final ';' is "
                                      "refused by Max 9.1.4 and 9.2.0 (probes R1450, R1451, R1452); only one plain "
                                      "statement may leave it out (probes R950, R952). Add ';'" % (end, what))
            else:
                # a lone while, only declarations: not measured
                self.notes.append({"rule": "G124", "sev": "warn", "line": end,
                                   "msg": "no ';' at the end of line %d. Only a codebox that is one plain statement "
                                          "(out1 = in1 or cos(in1)) was measured to work without it (probes R950, "
                                          "R952); after a function or a declaration, and for a lone if, Max refused it "
                                          "(probes R1007, R1008, R1200, R1201). This form was not measured. Add ';'"
                                          % end})
        return items

    def is_require(self):
        """require("lib") or require "lib" (probes R142, R183, R184)"""
        if self.text() != "require":
            return False
        if self.text(1) == "(":
            return self.peek(2) is not None and self.peek(2).kind == "str" and self.text(3) == ")"
        return self.peek(1) is not None and self.peek(1).kind == "str"

    def require(self):
        t = self.take()
        paren = self.text() == "("
        if paren:
            self.take()
        lib = self.take().text[1:-1]
        if paren:
            self.take(")")
        nosemi = self.text() != ";"      # ';' is optional after require (probes R142, R184)
        if not nosemi:
            self.take()
        return Node("require", t.line, lib=lib, nosemi=nosemi)

    def is_funcdef(self):
        """name(params) { : params may have defaults, uf(v, amp = 1) (probes R180, R181)"""
        t = self.peek()
        if t is None or t.kind != "id" or t.text in STMT_KW or self.text(1) != "(":
            return False
        depth = 0
        for j in range(self.p + 1, len(self.t)):
            x = self.t[j].text
            if x in (";", "{", "}"):
                return False
            if x in ("(", "["):
                depth += 1
            elif x in (")", "]"):
                depth -= 1
                if depth == 0:
                    return j + 1 < len(self.t) and self.t[j + 1].text == "{"
        return False

    def funcdef(self):
        name = self.take()
        self.take("(")
        inner = self.paren_rest()
        params, defaults = [], {}
        for part in split_commas(inner):
            if len(part) > 1 and all(t.kind == "id" and t.text not in STMT_KW for t in part):
                # 'f(a, b c)': refused also when the function is never called (probes R1104, R1105)
                raise ParseError(part[1].line, "function %s(): no ',' between the parameters %s. Max 9.1.4 and 9.2.0 "
                                               "refuse the codebox, also when the function is never called (probes "
                                               "R1104, R1105). Add ','"
                                 % (name.text, " and ".join("'%s'" % t.text for t in part)))
            if not part or part[0].kind != "id" or part[0].text in STMT_KW or (len(part) > 1 and part[1].text != "="):
                raise ParseError(part[0].line if part else name.line,
                                 "function %s(): a parameter must be a name or name = default value" % name.text)
            if len(part) > 1:
                if len(part) == 2:
                    raise ParseError(part[1].line, "function %s(): no default value after '%s ='" % (name.text, part[0].text))
                check_expr(part[2:], "rhs")
                defaults[part[0].text] = Expr(part[2:])
            params.append(part[0].text)
        saved, self.in_func, self.loops = self.loops, True, 0
        body = self.block()
        self.in_func, self.loops = False, saved
        return Node("func", name.line, name=name.text, params=params, defaults=defaults, body=body)

    def block(self):
        self.take("{")
        body = []
        while self.text() != "}":
            if self.peek() is None:
                raise ParseError(self.line(), "missing '}'")
            body.append(self.stmt())
        self.take("}")
        return body

    def body(self):
        """(statements, braced). Braces do not change scoping: a variable first set in an if/else body is
        local with or without them (probes P14, P23, R131)"""
        if self.text() == "{":
            return self.block(), True
        return [self.stmt()], False

    def loop_body(self):
        self.loops += 1
        try:
            return self.body()
        finally:
            self.loops -= 1

    def stmt(self):
        t = self.peek()
        if t is None:      # the code ends where a statement must come, e.g. right after 'if (x)' or 'else'
            raise ParseError(self.line(), "unexpected end of code: a statement is missing (after if / else / for / while?)")
        x = t.text
        if self.is_funcdef():
            raise ParseError(t.line, "function %s() is defined inside a block or another function. Define functions only "
                                     "at the top of the codebox, before all declarations and statements (Max refuses a "
                                     "function after a statement: 'function definitions not allowed here', probe P-07; "
                                     "a definition inside a block was not measured)" % x)
        if x in DECL_KW or (x in LOWER_DECL and self.peek(1) is not None and self.peek(1).kind == "id"
                            and self.text(1) not in STMT_KW):
            return self.decl()
        if x == "if":
            return self.if_()
        if x == "for":
            return self.for_()
        if x == "while":
            self.take()
            self.take("(")
            cond = self.paren_rest()
            check_expr(cond, "cond", t.line)
            body, braced = self.loop_body()
            return Node("while", t.line, cond=Expr(cond), body=body, braced=braced)
        if x == "return":
            if not self.in_func:
                raise ParseError(t.line, "return in the main code, outside a function. Max 9.1.4 and 9.2.0 refuse the "
                                         "codebox (probe R1205). Use return only inside a function; the main code sends "
                                         "values with out1 = ...;")
            self.take()
            e = self.until("return")
            if self.peek() is None:
                raise ParseError(t.line, "missing ';' after return. Max: jump statement missing ';' (probe R186)")
            self.take(";")
            if e:
                check_expr(e, "return")
            return Node("return", t.line, expr=Expr(e))
        if x in ("break", "continue"):
            if not self.loops:
                raise ParseError(t.line, "%s outside a for or while loop. Max 9.1.4 and 9.2.0 refuse the codebox (probe "
                                         "R1206). Use it only inside a loop body" % x)
            self.take()
            if self.text() != ";":
                raise ParseError(t.line, "missing ';' after %s (like return: Max says jump statement missing ';', "
                                         "probe R186)" % x)
            self.take()
            return Node("jump", t.line)
        if x == "{":
            raise ParseError(t.line, "a { } block without if, for or while. Max 9.1.4 and 9.2.0 refuse the codebox, "
                                     "also when the variable it sets was assigned before it (probes R1063-R1065, and "
                                     "R1236 inside a function). Remove the braces")
        if x == ";":
            self.take()
            return Node("empty", t.line)
        if x in ("else", "}"):
            raise ParseError(t.line, "unexpected %r" % x)
        toks = self.until()
        if self.peek() is not None:
            self.take(";")
        return simple(toks, t.line)

    def paren_rest(self):
        """after '(' : tokens up to the matching ')' (consumed)"""
        out, depth = [], 0
        while True:
            t = self.take()
            if t.text in ("(", "["):
                depth += 1
            elif t.text in (")", "]"):
                if depth == 0:
                    if t.text != ")":
                        raise ParseError(t.line, "unbalanced ']'")
                    return out
                depth -= 1
            elif t.text in ("{", "}", ";"):
                raise ParseError(t.line, "unexpected %r inside ( )" % t.text)
            out.append(t)

    def if_(self):
        t = self.take("if")
        self.take("(")
        cond = self.paren_rest()
        check_expr(cond, "cond", t.line)
        cond = Expr(cond)
        then, then_b = self.body()
        els, els_b = None, True
        if self.text() == "else":
            self.take()
            if self.text() == "if":
                els, els_b = [self.if_()], False
            else:
                els, els_b = self.body()
        return Node("if", t.line, cond=cond, then=then, els=els, then_braced=then_b, els_braced=els_b)

    def for_(self):
        t = self.take("for")
        o = self.p
        self.take("(")
        j = match_close(self.t, o)
        inside = self.t[o + 1:j]
        self.p = j + 1
        parts, cur, depth = [], [], 0
        for k in inside:
            if k.text in ("(", "["):
                depth += 1
            elif k.text in (")", "]"):
                depth -= 1
            if k.text == ";" and depth == 0:
                parts.append(cur)
                cur = []
            else:
                cur.append(k)
        parts.append(cur)
        if len(parts) != 3:
            raise ParseError(t.line, "for ( ; ; ) needs exactly two ';'")
        init = self.for_clause(parts[0], t.line, "start", "R1202, R1203")
        step = self.for_clause(parts[2], t.line, "step", "R1204")
        if parts[1]:
            check_expr(parts[1], "cond", t.line)
        cond = Expr(parts[1]) if parts[1] else None
        body, braced = self.loop_body()
        return Node("for", t.line, init=init, cond=cond, step=step, body=body, braced=braced)

    @staticmethod
    def for_clause(toks, line, what, probes):
        """statements of the start or step part of a for header. A ',' there fails on 9.1.4 and 9.2.0, both as
        GenExpr's multi-assignment 'i, j = 0, 1' (probe R1202) and C-style 'i = 0, j = 1' (probes R1203, R1204)"""
        parts = [p for p in split_commas(toks) if p]
        if len(parts) <= 1:
            return [simple(p, line) for p in parts]
        text = short(" ".join(t.text for t in toks).replace(" ,", ","), 30)
        raise ParseError(toks[0].line, "for loop %s part '%s': a ',' in a for header. Max 9.1.4 and 9.2.0 refuse the "
                                       "codebox, as a multi-assignment 'i, j = 0, 1' and C-style 'i = 0, j = 1' alike "
                                       "(probes %s). Assign the other variable before the loop or in its body"
                                       % (what, text, probes))

    def decl(self):
        kw = self.take()
        kind = LOWER_DECL.get(kw.text, kw.text)
        items = []
        while True:
            name = self.take()
            if name.kind != "id":
                raise ParseError(name.line, "expected a name after %s" % kw.text)
            args, named = [], {}
            if self.text() == "=":         # 'Param g = 0.5;' (a C-style initializer)
                val = []
                while self.peek(len(val) + 1) is not None and self.text(len(val) + 1) not in (";", "{", "}"):
                    val.append(self.text(len(val) + 1))
                raise ParseError(name.line, "%s %s = ...: a declaration takes its value in ( ), not after '='. Write "
                                            "%s %s(%s);" % (kw.text, name.text, kind, name.text,
                                                            short(" ".join(val), 30) if val else "0"))
            if self.text() == "(":
                self.take()
                inner = self.paren_rest()
                check_call_args(name, inner)
                c = Expr._call(name.text, None, name.line, inner)
                args, named = c.args, c.named
            items.append((name.text, name.line, args, named))
            if self.text() == ",":
                self.take()
                continue
            node = Node("decl", kw.line, kw=kind, items=items, lower=kw.text if kw.text != kind else None)
            last = self.t[self.p - 1].line
            if self.peek() is None:
                self.open_end = last
                return node
            if self.text() != ";":
                raise ParseError(last, missing_semicolon(last, "R187, R188"))
            self.take(";")
            return node


def simple(toks, line):
    """assignment (a, b = e / a += e) or expression statement"""
    j = 0
    while j < len(toks) and toks[j].kind == "id":
        if j + 1 < len(toks) and toks[j + 1].text == ",":
            j += 2
            continue
        break
    if j < len(toks) and toks[j].kind == "id" and j + 1 < len(toks) and toks[j + 1].text in ASSIGN_OPS:
        targets = [(toks[k].text, toks[k].line) for k in range(0, j + 1, 2)]
        if not toks[j + 2:]:
            raise ParseError(toks[j + 1].line, "nothing after '%s'" % toks[j + 1].text)
        check_expr(toks[j + 2:], "rhs")
        return Node("assign", toks[0].line, targets=targets, op=toks[j + 1].text, expr=Expr(toks[j + 2:]))
    if not toks:
        return Node("empty", line)
    check_expr(toks, "stmt")
    return Node("expr", toks[0].line, expr=Expr(toks))


# ----------------------------------------------------------------- analysis


def walk_nodes(items, in_func=False):
    """yield (node, in_func) for every statement, depth first"""
    for n in items:
        yield n, in_func
        if n.kind == "func":
            for x in walk_nodes(n.body, True):
                yield x
        elif n.kind == "if":
            for x in walk_nodes(n.then, in_func):
                yield x
            for x in walk_nodes(n.els or [], in_func):
                yield x
        elif n.kind == "for":
            for x in walk_nodes(n.init + n.step + n.body, in_func):
                yield x
        elif n.kind in ("while", "block"):
            for x in walk_nodes(n.body, in_func):
                yield x


def node_exprs(n):
    if n.kind in ("assign", "expr", "return"):
        return [n.expr]
    if n.kind == "if":
        return [n.cond]
    if n.kind == "while":
        return [n.cond]
    if n.kind == "for":
        return [n.cond] if n.cond else []
    if n.kind == "decl":
        out = []
        for _, _, args, named in n.items:
            out += args + list(named.values())
        return out
    return []


def branch_kind(f):
    """how a user function returns through a branch, or None: a ?: in a return (probes R1303, R1332-R1335, R1524),
    a return inside an if block (R1545, R1547), or a returned variable that an if block assigns (R1520-R1522). All
    fail inside a write value on Max 9.1.x"""
    for x, _ in walk_nodes(f.body, True):
        if x.kind == "return" and any(t.text == "?" for t in x.expr.toks):
            return "returns a ?: expression"
    in_if = set()
    for x, _ in walk_nodes(f.body, True):
        if x.kind == "if":
            for y, _ in walk_nodes(x.then + (x.els or []), True):
                if y.kind == "return":
                    return "returns inside an if block"
                if y.kind == "assign":
                    in_if.update(t for t, _ in y.targets)
    for x, _ in walk_nodes(f.body, True):
        if x.kind == "return" and len(x.expr.toks) == 1 and x.expr.toks[0].text in in_if:
            return "returns '%s', which an if block sets" % x.expr.toks[0].text
    return None


def is_write(c):
    """poke(d, v, ...), d.poke(v, ...) or d.write(v)"""
    return (c.obj is not None and c.name in ("poke", "write")) or (c.obj is None and c.name == "poke")


def raw_trig(e):
    """sin/cos reaches this expression without passing through wrap/abs/fold/clamp/clip"""
    for c in e.calls:
        if c.obj is None and c.name in ("sin", "cos", "fastsin", "fastcos"):
            return True
        if c.obj is None and c.name in ("wrap", "abs", "fold", "clamp", "clip", "fract"):
            continue
        if any(raw_trig(a) for a in c.args):
            return True
    return False


# G410: a Param read only inside these is a time or a pitch, not a loop gain
TIME_PITCH_CALLS = {"mstosamps", "sampstoms", "exp", "mtof", "t60", "t60time"}
# G410: a loop through these still rings (small signals pass almost unchanged), but its level stays bounded
BOUNDED_CALLS = {"sin", "cos", "fastsin", "fastcos", "tanh", "atan", "clamp", "clip", "fold", "wrap"}


def reads_outside(e, name, calls):
    """reads of name in e that are not inside a call of a function in calls"""
    n = sum(1 for r, _ in e.reads if r == name)
    for c in e.calls:
        if not (c.obj is None and c.name in calls):
            n += sum(reads_outside(a, name, calls) for a in c.args + list(c.named.values()))
    return n


def is_require(n):
    return n.kind == "require"


EVAL_MAX = 1000   # longer constant expressions are not evaluated: a run of 200000 '-' overflowed Python 3.9's C stack


def safe_eval(s):
    """float value of s (numbers and + - * / ( ) only, checked by the caller), else None"""
    if len(s) > EVAL_MAX:
        return None
    try:
        return float(eval(s, {"__builtins__": {}}, {}))
    except Exception:
        return None


def num_value(expr):
    """value of an expression made only of numbers and + - * / ( ), else None"""
    s = "".join(t.text for t in expr.toks)
    if not s or not re.fullmatch(r"[0-9.eE+\-*/() ]+", s):
        return None
    return safe_eval(s)


# ----------------------------------------------------------------- main code: definitions and liveness

CONST, UNKNOWN, NONCONST = 0, 1, 2      # is a value a compile-time constant for Max?
OUT_NAME = re.compile(r"out\d*$")
IN_NAME = re.compile(r"in\d*$")
CONST_OPS = {"+", "-", "*", "/", "(", ")"}   # constant expressions: 2 * 3 (probe R900), -5 (probe R911)
# operators that keep an expression of constants constant: 7 % 4 (probe R1069), 2 > 1 (probe R1068); and ',' between
# call arguments
CONST_EXPR_OPS = CONST_OPS | {"%", "<", ">", "<=", ">=", "==", "!=", "&&", "||", "^^", "!", ","}
# math constants that leak out of a block like numbers: pi (probe R901), twopi (probe R1066). samplerate does not (R902)
MATH_CONSTANTS = {"pi", "twopi", "halfpi", "invpi", "degtorad", "radtodeg", "ln2", "ln10", "log2e", "log10e", "sqrt2",
                  "sqrt1_2", "phi", "e"}
CONST_VALUES = {"pi": math.pi, "twopi": 2 * math.pi}   # values shown in messages: measured (probes R901, R1066)
# operators without state: a call of one on constants is a constant, abs(-3) (probe R1067). Gen reference categories,
# and the names used without the reference
PURE_CATEGORIES = {"numeric", "math", "trigonometry", "powers", "comparison", "logic", "convert", "range"}
# 'convert' operators that read the sample rate: not constants (a samplerate value leaks nowhere: probe R902)
SAMPLERATE_OPS = {"mstosamps", "sampstoms"}
PURE_FALLBACK = set("abs ceil floor round trunc sign fract min max pow sqrt exp exp2 log log2 log10 ln sin cos tan "
                    "tanh atan atan2 asin acos clamp clip wrap fold scale mod div atodb dbtoa mtof ftom".split())
SEV_RANK = {"info": 0, "warn": 1, "error": 2}
# rules Max applies to every function body, also of a function that is never called: a declaration after a statement
# (probe R1040). Other errors in a function that is never called do not happen (probes R207, R319, R443, R1041)
EVERY_FUNCTION = {"G101"}
KEPT_BY_NAME = ("the condition of a statement inside a block that Max keeps only because its variable is read after "
                "the block (probes R303, R224, R1060 measured the statement's own reads, not its condition)")
BLOCK_WORDS = {"if": "the if block", "else": "the else branch", "for": "the for loop", "while": "the while loop",
               "plain": "the { } block"}


def effect_words(x):
    """'poke' -> 'a poke', 'out2 =' -> 'an assignment to out2' (Analyzer.body_effects names)"""
    m = re.match(r"(out\d*) =( inside a block)?$", x)
    if m:
        return "an assignment to %s%s" % (m.group(1), m.group(2) or "")
    return x if x.endswith("()") else "a " + x


def short(text, n=40):
    return text if len(text) <= n else text[:n - 3] + "..."


def sentences(*parts):
    """join message parts (empty ones skipped) into sentences"""
    return ". ".join(p for p in parts if p)


def pretty(e):
    """source-like text of an expression: cartopol(in1, 0.5), -5, a * -1"""
    out, prev, prev2 = "", None, None
    for t in e.toks:
        x = t.text
        unary = (prev is not None and prev.text in ("-", "+", "!") and
                 (prev2 is None or (prev2.kind == "op" and prev2.text != ")")))
        if prev is None or x in (")", ",", ".") or prev.text in ("(", ".") or (x == "(" and prev.kind == "id") or unary:
            out += x
        else:
            out += " " + x
        prev2, prev = prev, t
    return out


MULTI_NOTE = ("Only a warn for this comma list: Max judges each item of 'a, b = x, y' on its own (a constant item leaks "
              "like a plain constant, probes R1222, R1223; an unused item is dropped, probe R1224), but here the items "
              "do not pair up one value per name (or the operator is not '='), which was not measured")


class _Blk:
    """a block of the main code: 'top', 'if', 'else', 'for', 'while' or 'plain' ({ } alone)"""
    __slots__ = ("kind", "parent", "line", "cond", "end", "defs", "loop")

    def __init__(self, kind, parent, line):
        self.kind, self.parent, self.line = kind, parent, line
        self.cond = None          # statement record of the condition that controls this block
        self.end = None           # index of the last statement record inside the block
        self.defs = []            # assignments whose innermost block is this one
        self.loop = kind in ("for", "while") or bool(parent is not None and parent.loop)


class _St:
    """one statement (or condition) of the main code, in program order"""
    __slots__ = ("idx", "block", "line", "uses", "targets", "op", "rhs", "sink", "why", "level", "nlevel", "nwhy", "multi",
                 "items", "tnames", "isink", "iswhy", "ilevel", "iwhy", "inlevel", "inwhy")

    def __init__(self, idx, block, line):
        self.idx, self.block, self.line = idx, block, line
        self.multi = False            # a comma list whose items do not pair up with the names: not measured
        self.uses, self.targets, self.op, self.rhs = [], set(), None, None
        self.sink = self.level = 0    # 2 = reaches a measured sink, 1 = only an unmeasured one, 0 = dead
        self.why = None               # for level 1: the unmeasured sink
        self.nlevel, self.nwhy = 0, None   # kept only because its name is read after its block (R303, R224)
        # 'a, b = x, y' with one value per name: Max judges each item on its own (probes R1222-R1224), so each item
        # has its own level; level / nlevel above are then the highest of the items
        self.items = self.tnames = self.isink = self.iswhy = None
        self.ilevel = self.iwhy = self.inlevel = self.inwhy = None


class _Def:
    # multi: one name of 'a, b = x, y' (constness per item not measured); zero: an extra name of 'a, b = x' (gets 0,
    # probe R642)
    __slots__ = ("name", "st", "block", "rhs", "op", "selfref", "end", "line", "const", "multi", "zero", "item")


class _Use:
    # item: the item of 'a, b = x, y' that this read belongs to (None outside such a statement)
    __slots__ = ("name", "st", "line", "rd", "visible", "leak", "both", "compound", "item")


def _merge(a, b):
    if a is b:
        return a
    out = dict(a)
    for k, v in b.items():
        w = out.get(k)
        out[k] = v if w is None or w is v else w | v
    return out


class MainFlow:
    """Assignments, reaching assignments and liveness of the main code (user function bodies are not part of it).
    Model measured in Max 9.2.0 with audio on (rounds 9-14):
    - a value counts ('is live') when it reaches an output, a History write (even of a History that is never read:
      probes R418, R434), a Delay write (R700), a poke (R411) or a user function that pokes (R1072). Every output and
      History write counts, also one overwritten later (R1076, R1077). Max drops the other statements before it
      checks names, so their errors do not happen (R220, R221, R300, R301, R304, R422, R433, R437)
    - at the top level every other assignment is its own value: one overwritten before any use is dropped (R301)
    - an assignment inside a block counts when its name is read by a live statement anywhere after the block, even
      after a top-level overwrite (R303, R224), or when its value reaches a live read
    - names are looked up in program order: a variable is visible after an assignment at the same or an enclosing
      block level. One first assigned inside a closed block is visible after it only in the 'constant leak' way
      (rounds 12-14), which Analyzer.block_var_read() judges"""

    def __init__(self, items, decl_kind, user_func, effects, abstractions, ref, old=False):
        self.decl_kind, self.user_func, self.effects = decl_kind, user_func, effects
        self.abstractions, self.ref = abstractions, ref
        self.old = old                        # judge by Max 9.1.x (rounds 16: R1060, R1061, R1070, R1071, R1080)
        self.sts, self.uses, self.by_name, self.def_list, self.all_defs = [], {}, {}, {}, []
        self.def_of, self.gen_memo = {}, {}
        self.jumps = {}                       # id(loop block) -> records of its break / continue statements
        self.st_of = {}                       # id(statement node) -> its record (the condition's for if / loops)
        self.top = _Blk("top", None, 0)
        self.frames = [self.frame()]
        main = [n for n in items if n.kind not in ("func", "require")]
        self.end_state = self.walk(main, self.top, {}, True)
        self.liveness()
        for d in self.all_defs:               # in program order, so a long chain of copies recurses one step each
            self.const_def(d, set())

    @staticmethod
    def norm(name):
        return "out1" if name == "out" else name      # bare out is out1 (probe R954)

    # ---- lexical scopes: which assignments a read can see
    @staticmethod
    def frame():
        return {"names": set(), "defs": {}, "leak": {}}

    def visible(self, name):
        return any(name in f["names"] for f in self.frames)

    def define(self, name, d):
        f = self.frames[-1]
        if not self.visible(name):
            f["names"].add(name)
        f["defs"].setdefault(name, []).append(d)

    def push(self):
        self.frames.append(self.frame())

    def pop(self):
        """close a block: its assignments of names not visible outside it 'leak' into the enclosing level"""
        child = self.frames.pop()
        parent = self.frames[-1]
        leaked = set()
        for name, ds in child["defs"].items():
            parent["defs"].setdefault(name, []).extend(ds)
            if not self.visible(name):
                ent = parent["leak"].setdefault(name, ([], []))
                ent[0].extend(ds)
                sub = child["leak"].get(name)
                if sub:
                    ent[1].extend(sub[1])
                leaked.add(name)
        return leaked

    # ---- walk: reaching assignments (state: name -> frozenset of _Def) and records
    def new_st(self, block, line):
        st = _St(len(self.sts), block, line)
        self.sts.append(st)
        return st

    def get_def(self, n, i, name):
        key = (id(n), i)
        d = self.def_of.get(key)
        if d is None:
            d = _Def()
            d.name, d.st, d.block, d.rhs, d.op = self.norm(name), None, None, None, None
            d.selfref, d.end, d.line, d.const = False, False, n.line, None
            d.multi = d.zero = False
            d.item = None
            self.def_of[key] = d
        return d

    def use(self, st, name, line, state, key, compound=False):
        u = _Use()
        u.name, u.st, u.line, u.compound = name, st, line, compound
        u.item = None
        u.rd = state.get(self.norm(name), frozenset())
        u.visible = self.visible(name)
        u.leak = u.both = None
        if not u.visible:
            defs, both = [], []
            for f in self.frames:
                e = f["leak"].get(name)
                if e:
                    defs += e[0]
                    both += e[1]
            if defs:
                u.leak, u.both = defs, both
        st.uses.append(u)
        self.uses[key] = u
        self.by_name.setdefault(self.norm(name), []).append(u)

    def expr_uses(self, e, st, state):
        for k, (name, line) in enumerate(e.all_reads()):
            self.use(st, name, line, state, (id(e), k))
        st.sink = max(st.sink, self.sink(e, st))

    def sink(self, e, st):
        """2: a poke, a Delay write or a user function that pokes (measured, probes R411, R700, R1072); 1: a call
        whose effect was not measured here (user function with other side effects, abstraction, splat, Data/Buffer
        .poke/.write)"""
        lv = 0
        for c in e.all_calls():
            if c.obj is None:
                if c.name == "poke" or (self.user_func(c.name) and self.effects(c.name) == 2):
                    return 2                  # a user function that pokes counts like a poke (probe R1072)
                if c.name == "splat" or (self.user_func(c.name) and self.effects(c.name)) or \
                        c.name in self.abstractions or \
                        (self.ref and not self.user_func(c.name) and not self.ref.callable(c.name)
                         and c.name not in NOT_CALLABLE and c.name not in self.decl_kind):   # dl(10) on a Delay: G105
                    lv, st.why = 1, "%s()" % c.name
            elif self.decl_kind.get(c.obj) == "Delay" and c.name == "write":
                return 2
            elif c.name in ("poke", "write", "splat"):
                lv, st.why = 1, "%s.%s()" % (c.obj, c.name)
        return lv

    def walk(self, stmts, block, state, rec):
        for n in stmts:
            state = self.node(n, block, state, rec)
        return state

    def node(self, n, block, state, rec):
        """state after statement n. rec=False only computes reaching assignments (for loop bodies)"""
        k = n.kind
        if k == "assign":
            st = None
            if rec:
                st = self.new_st(block, n.line)
                self.st_of[id(n)] = st
                st.op, st.rhs = n.op, n.expr
                nparts = len(split_commas(n.expr.toks)) if len(n.targets) > 1 else 1
                st.multi = nparts > 1
                if n.op != "=":
                    for name, line in n.targets:
                        self.use(st, name, line, state, ("compound", id(n), name), True)
                self.expr_uses(n.expr, st, state)
                if any(OUT_NAME.match(self.norm(t)) or self.decl_kind.get(t) == "History" for t, _ in n.targets):
                    st.sink = 2           # every output or History write counts, also one overwritten later (R1076, R1077)
                reads = {u.name for u in st.uses}
                items = self.items_of(n, st, state) if st.multi and nparts == len(n.targets) else None
                if items is not None and n.op == "=" and self.split_items(n, st, items):
                    st.multi = False              # judged item by item (probes R1222-R1224)
                else:
                    items = None
            for i, (name, line) in enumerate(n.targets):    # every caller owns state: changed in place
                d = self.get_def(n, i, name)
                if rec:
                    d.st, d.block, d.rhs, d.op, d.line = st, block, n.expr, n.op, line
                    d.selfref = n.op != "=" or name in reads
                    d.multi = st.multi
                    if items is not None:
                        d.rhs, d.item = items[i], i   # each item on its own (probes R1222, R1223, R1224)
                        d.selfref = name in {x for x, _ in items[i].all_reads()}
                    # 'a, b = 5': b gets 0 (probe R642); after a call (several outputs) it gets one of them
                    d.zero = (i > 0 and nparts == 1 and n.op == "=" and not (n.expr.calls and n.expr.calls[0].start == 0
                                                                             and n.expr.calls[0].end == len(n.expr.toks) - 1))
                    st.targets.add(name)
                    block.defs.append(d)
                    self.all_defs.append(d)
                    self.def_list.setdefault(name, []).append((st.idx, line))
                    self.define(name, d)
                state[d.name] = frozenset((d,))
            return state
        if k in ("expr", "return"):
            if rec:
                st = self.new_st(block, n.line)
                self.st_of[id(n)] = st
                self.expr_uses(n.expr, st, state)
                if k == "return" or getattr(n, "implicit", False):
                    st.sink = 2 if k == "expr" else max(st.sink, 1)   # a lone expression goes to out1 (R952)
                    st.why = st.why or "return"
            return state
        if k == "if":
            cond = None
            if rec:
                cond = self.new_st(block, n.line)
                self.st_of[id(n)] = cond
                self.expr_uses(n.cond, cond, state)
            s1, l1 = self.body(n.then, "if", block, n.line, cond, dict(state), rec)
            if n.els is None:
                s2, l2 = state, set()
            else:
                s2, l2 = self.body(n.els, "else", block, n.line, cond, dict(state), rec)
            if rec:
                for name in l1 & l2:          # assigned in both branches, not before (probes R401, R904)
                    self.frames[-1]["leak"][name][1].append(n.line)
            return _merge(s1, s2)
        if k in ("for", "while"):
            if k == "for":
                for s in n.init:              # the loop variable belongs to the enclosing block (probe P13)
                    state = self.node(s, block, state, rec)
            head = _merge(state, self.gen(n))
            if not rec:
                return head
            b = _Blk(k, block, n.line)
            self.push()
            cond = b.cond = self.new_st(block, n.line)
            self.st_of[id(n)] = cond
            if n.cond is not None:
                self.expr_uses(n.cond, cond, head)
            s = self.walk(n.body, b, dict(head), True)
            for x in (n.step if k == "for" else ()):
                s = self.node(x, b, s, True)
            b.end = len(self.sts) - 1
            g = self.gen(n)
            for d in b.defs:
                d.end = d in g.get(d.name, ())
            self.pop()
            return head
        if k == "block":
            s, _ = self.body(n.body, "plain", block, n.line, None, state, rec)
            return s
        if k == "jump" and rec:
            # break / continue change how often the loop body runs (probe R955: break gave s = 3): it counts when
            # anything in its loop counts, and then so does the condition that decides whether it runs
            loop = block
            while loop is not None and loop.kind not in ("for", "while"):
                loop = loop.parent
            if loop is not None:
                self.jumps.setdefault(id(loop), []).append(self.new_st(block, n.line))
        return state

    def items_of(self, n, st, state):
        """the values of 'a, b = x, y' as separate expressions, their reads recorded on the statement: Max judges each
        item's value on its own for a constant (probes R1222, R1223). None if they cannot be split"""
        try:
            items = [Expr(p) for p in split_commas(n.expr.toks)]
        except ParseError:
            return None
        for e in items:
            for k, (name, line) in enumerate(e.all_reads()):
                self.use(st, name, line, state, (id(e), k))
        return items

    def split_items(self, n, st, items):
        """'a, b = x, y': give each read of the statement its item and each item its own sink (an output or History
        name, or a poke in that item). False if the reads cannot be matched to the items"""
        whole = n.expr
        reads = whole.all_reads()
        owner = []
        for i, e in enumerate(items):         # top-level reads of the whole list, in token order
            owner += [i] * len(e.reads)
        if len(owner) != len(whole.reads):
            return False
        calls = []
        for i, e in enumerate(items):
            calls += [i] * len(e.calls)
        if len(calls) != len(whole.calls):
            return False
        for c, i in zip(whole.calls, calls):  # then the reads inside each call's arguments
            owner += [i] * sum(len(a.all_reads()) for a in c.args + list(c.named.values()))
        if len(owner) != len(reads):
            return False
        for k, i in enumerate(owner):
            u = self.uses.get((id(whole), k))
            if u is None or u.st is not st:
                return False
            u.item = i
        for i, e in enumerate(items):
            for k in range(len(e.all_reads())):
                u = self.uses.get((id(e), k))
                if u is not None:
                    u.item = i
        k = len(items)
        st.items, st.tnames = k, [t for t, _ in n.targets]
        st.isink, st.iswhy = [0] * k, [None] * k
        st.ilevel, st.iwhy, st.inlevel, st.inwhy = [0] * k, [None] * k, [0] * k, [None] * k
        st.sink, st.why = 0, None
        for i, e in enumerate(items):
            t = self.norm(st.tnames[i])
            if OUT_NAME.match(t) or self.decl_kind.get(st.tnames[i]) == "History":
                st.isink[i] = 2
            else:
                st.why = None
                st.isink[i] = self.sink(e, st)
                st.iswhy[i] = st.why
            st.sink = max(st.sink, st.isink[i])
        st.why = None
        return True

    def body(self, stmts, kind, parent, line, cond, state, rec):
        if not rec:
            return self.walk(stmts, None, state, False), set()
        b = _Blk(kind, parent, line)
        b.cond = cond
        self.push()
        state = self.walk(stmts, b, state, True)
        b.end = len(self.sts) - 1
        for d in b.defs:
            d.end = d in state.get(d.name, ())
        return state, self.pop()

    def gen(self, n):
        """assignments inside loop n that may reach the end of its body (one pass, memoized; inner loops reuse
        theirs, so nested loops stay linear)"""
        g = self.gen_memo.get(id(n))
        if g is None:
            g = self.walk(list(n.body) + list(n.step if n.kind == "for" else ()), None, {}, False)
            self.gen_memo[id(n)] = g
        return g

    # ---- liveness
    def level_of(self, u):
        """(level, why) of read u: 2 its value is used (measured), 1 only through something not measured (why), 0
        dropped by Max. A statement kept only because its name is read after its block counts as used: on Max 9.2.0
        for all its reads (x -= 1: probes R303, R224; t = x: probe R1060), on 9.1.x only for the read of its own
        variable (R303 fails there too, R1060 runs)"""
        st = u.st
        if st.items is not None and u.item is not None:     # one item of 'a, b = x, y' (probe R1224)
            i = u.item
            level, why, nlevel, nwhy = st.ilevel[i], st.iwhy[i], st.inlevel[i], st.inwhy[i]
            own = {self.norm(st.tnames[i])}
        else:
            level, why, nlevel, nwhy = st.level, st.why, st.nlevel, st.nwhy
            own = {self.norm(t) for t in st.targets}
        if self.old and self.norm(u.name) not in own:
            cand = (0, None)
        else:
            cand = (nlevel, nwhy)
        return (level, why) if level >= cand[0] else cand

    def liveness(self):
        work = []

        def lift(st, lv, why, item=None):
            if st is None:
                return
            if st.items is not None:          # 'a, b = x, y': each item has its own level (probe R1224)
                changed = False
                for i in (range(st.items) if item is None else (item,)):
                    if st.ilevel[i] < lv:
                        st.ilevel[i], st.iwhy[i] = lv, (why if lv == 1 else None)
                        changed = True
                if st.level < lv:
                    st.level, st.why = lv, (why if lv == 1 else None)
                if changed:
                    work.append(st)
                return
            if st.level < lv:
                st.level = lv
                st.why = why if lv == 1 else None
                work.append(st)

        def nlift(st, lv, why, item=None):
            if st is None:
                return
            if st.items is not None:
                changed = False
                for i in (range(st.items) if item is None else (item,)):
                    if st.inlevel[i] < lv:
                        st.inlevel[i], st.inwhy[i] = lv, (why if lv == 1 else None)
                        changed = True
                if st.nlevel < lv:
                    st.nlevel, st.nwhy = lv, (why if lv == 1 else None)
                if changed:
                    work.append(st)
                return
            if st.nlevel < lv:
                st.nlevel, st.nwhy = lv, (why if lv == 1 else None)
                work.append(st)

        for st in self.sts:
            if st.items is not None:
                for i in range(st.items):
                    if st.isink[i]:
                        lift(st, st.isink[i], st.iswhy[i], i)
            elif st.sink:
                why, st.why = st.why, None
                lift(st, st.sink, why)
        for name, ds in self.end_state.items():   # the final value of an output or History is used
            if OUT_NAME.match(name) or self.decl_kind.get(name) == "History":
                for d in ds:
                    lift(d.st, 2, None, d.item)
        exported = {}       # name -> assignments inside a block that reach the end of their block
        for d in self.all_defs:
            if d.block is not self.top and d.end:
                exported.setdefault(d.name, []).append(d)
        while work:
            st = work.pop()
            for u in st.uses:
                lv, why = self.level_of(u)
                if not lv:
                    continue
                for d in u.rd:
                    lift(d.st, lv, why, d.item)
                for d in exported.get(self.norm(u.name), ()):
                    if d.block.end < st.idx:      # read anywhere after the block (probes R303, R224)
                        nlift(d.st, lv, why, d.item)
            lv, why = (st.level, st.why) if st.level or not st.nlevel else (1, KEPT_BY_NAME)
            if lv and self.jumps:
                b = st.block
                while b is not None:
                    for j in self.jumps.get(id(b), ()):
                        lift(j, lv, why)
                    b = b.parent
            b = st.block
            while b is not None and b.cond is None and b.kind == "plain":
                b = b.parent
            if lv and b is not None and b.cond is not None:
                lift(b.cond, lv, why)             # the condition that decides whether st runs

    # ---- queries for Analyzer
    def first_def(self, name, idx):
        """line of the first assignment to name at or after statement idx, else None"""
        for i, line in self.def_list.get(name, ()):
            if i >= idx:
                return line
        return None

    def later_live_use(self, name, idx):
        best = None
        for u in self.by_name.get(self.norm(name), ()):
            if u.st.idx > idx and self.level_of(u)[0] and (best is None or u.st.idx < best.st.idx):
                best = u
        return best

    @staticmethod
    def stmt_text(st, name):
        """'x -= 1' / 'x = x + 1' for an assignment statement"""
        return "%s %s %s" % (name, st.op, pretty(st.rhs)) if st.rhs is not None else name

    def leak_class(self, d):
        """is assignment d (inside a block) a compile-time constant, for a read after the block (rounds 13-14)"""
        if d.selfref:
            if any(u.leak for u in d.st.uses if self.norm(u.name) == d.name):
                return UNKNOWN                # updates a constant leaked from an earlier block: not measured
            return NONCONST                   # t = 5; t = t * 2 in one block (probe R807), a loop counter (R606)
        return self.const_def(d, set())

    def const_value(self, d, depth=0):
        """numeric value of a constant assignment (a number, pi, or a variable holding one), else None"""
        if d.zero:
            return 0.0
        if d.rhs is None or d.op != "=" or depth > 50 or d.multi:
            return None
        v = num_value(d.rhs)
        if v is not None:
            return v
        toks = d.rhs.toks
        if d.rhs.calls or any(t.kind == "str" or (t.kind == "op" and t.text not in CONST_OPS) for t in toks):
            return None
        text, k = [], 0                       # numbers, + - * / ( ) and variables that hold one constant (a * 2)
        for t in toks:
            if t.kind != "id":
                text.append(t.text)
                continue
            u = self.uses.get((id(d.rhs), k))
            k += 1
            low = t.text.lower() if t.text.isupper() else t.text
            x = (CONST_VALUES.get(low) if low in MATH_CONSTANTS and (u is None or not u.rd) else
                 self.const_value(next(iter(u.rd)), depth + 1) if u is not None and u.visible and len(u.rd) == 1
                 else None)
            if x is None:
                return None
            text.append("(%r)" % x)
        return safe_eval("".join(text))

    def const_use(self, u, seen):
        """is the value read by u a compile-time constant: numbers and pi are (R900, R901, R911), a top-level
        variable holding one is (R925); inlets, elapsed, samplerate, Params and Histories are not (R800, R804,
        R902, R903, R907), nor a loop counter (R606)"""
        name = u.name
        if IN_NAME.match(name) or name in ("elapsed", "samplerate", "SAMPLERATE"):
            return NONCONST
        if (name in MATH_CONSTANTS or (name.isupper() and name.lower() in MATH_CONSTANTS)) and not u.rd:
            return CONST
        kind = self.decl_kind.get(name)
        if kind in ("Param", "History"):
            return NONCONST
        if kind or OUT_NAME.match(name) or not u.visible or not u.rd:
            return UNKNOWN
        c = CONST
        for d in u.rd:                        # a loop, not max(generator): deep chains stay plain Python calls
            c = max(c, self.const_reaching(d, seen, u.st.block))
        return c

    def const_reaching(self, d, seen, block=None):
        """is the value of assignment d, read in block, a compile-time constant. Max 9.2.0: a value assigned inside
        a block never is, also a constant read in the same block (a = 5; t = a * 2: probe R1070) or merged with a
        top-level one (probe R1071). Max 9.1.x folds a constant read in the same block (R1070 gives t = 10)"""
        if d.block is not self.top:
            if d.selfref and d.block.loop:
                return NONCONST                   # a counter that changes in a loop (probe R606)
            c = self.const_def(d, seen)
            if not self.old:
                return NONCONST
            return c if d.block is block else NONCONST if c == NONCONST else UNKNOWN
        return self.const_def(d, seen)

    def const_def(self, d, seen):
        if d.const is not None:
            return d.const
        if d.zero:
            return CONST                      # an extra name of 'a, b = x' gets the constant 0 (probe R642)
        if d.multi:
            return UNKNOWN                    # 'a, b = 1, in1': whether Max judges each item on its own: not measured
        if d in seen or d.rhs is None:
            return UNKNOWN
        seen.add(d)
        c = self.const_expr(d.rhs, seen)
        if d.op != "=":
            c = max(c, CONST if d.op in ("+=", "-=", "*=", "/=") else UNKNOWN)
            for u in d.st.uses:
                if u.compound and self.norm(u.name) == d.name:
                    c = max(c, self.const_use(u, seen))
        seen.discard(d)
        d.const = c
        return c

    def pure_op(self, name):
        """a Gen operator without state (abs, min, pow, ...), not a user function or abstraction"""
        if self.user_func(name) or name in self.abstractions or name in SAMPLERATE_OPS:
            return False
        if self.ref:
            o = self.ref.ops.get(name)
            return bool(o) and o["cat"] in PURE_CATEGORIES
        return name in PURE_FALLBACK

    def const_expr(self, e, seen):
        c = CONST
        for call in e.all_calls():
            if call.obj is None and call.name in SAMPLERATE_OPS:
                return NONCONST                   # t = mstosamps(10) in a block fails like samplerate (probes R1460, R902)
            if call.obj is not None or call.named or not self.pure_op(call.name):
                c = UNKNOWN
        for t in e.toks:
            if t.kind == "str" or (t.kind == "op" and t.text not in CONST_EXPR_OPS):
                c = UNKNOWN
        for k in range(len(e.all_reads())):
            u = self.uses.get((id(e), k))
            c = max(c, self.const_use(u, seen) if u is not None else UNKNOWN)
            if c == NONCONST:
                break
        return c


class Analyzer:
    def __init__(self, items, ref, old_idents=None, old_decls=None, abstractions=(), lib_funcs=None, max_version=None,
                 patcher_params=(), patcher_complete=False):
        self.items, self.ref = items, ref
        self.patcher_params = set(patcher_params)   # [param NAME] boxes of the gen patcher (--param)
        self.patcher_complete = patcher_complete    # the gen patcher has no other named box (--complete-params)
        self.max_version_text = max_version or (ref.max_version() if ref else None) or "unknown"
        self.max_version = parse_version(self.max_version_text)
        self.abstractions = set(abstractions)
        self.findings = []
        self.seen = {}           # (rule, key) -> rank of the most severe finding added for it
        self.decls = {}          # name -> (kind, line, args, named)
        self.funcs = {}          # a name defined twice: Max ran the first definition (probe R1049, see dup_first_measured)
        for n in items:
            if n.kind == "func":
                self.funcs.setdefault(n.name, n)
        self.func_defs = {}
        for n in items:
            if n.kind == "func":
                self.func_defs.setdefault(n.name, []).append(n)
        self.lib_replaced = sorted(name for name in (lib_funcs or {}) if name in self.funcs)
        for name, node in (lib_funcs or {}).items():
            self.funcs.setdefault(name, node)
        self.old_idents, self.old_decls = old_idents, old_decls
        # every assignment (outside functions): name -> [(line, expr)]
        self.defs = {}
        for n, in_func in walk_nodes(items):
            if n.kind == "assign" and not in_func:
                for name, line in n.targets:
                    self.defs.setdefault(name, []).append((line, n.expr, n.op))
        self.top_names = set(self.defs)
        self.read_names = set()          # read in the main code; a function cannot see main-code names (probe R200)
        for n, in_func in walk_nodes(items):
            if not in_func:
                for e in node_exprs(n):
                    self.read_names |= {x for x, _ in e.all_reads()}
        for n in items:
            if n.kind == "decl":
                self.top_names |= {it[0] for it in n.items}
        self.in_func = self.lib_ctx = None
        self.reach = self.reachable()
        self.fract_ok, self.range_flow = set(), {}

    @staticmethod
    def calls_in(nodes):
        """names of the plain calls f(...) in these statements (and in the blocks inside them)"""
        out = set()
        for n, _ in walk_nodes(nodes):
            for e in node_exprs(n):
                out |= {c.name for c in e.all_calls() if c.obj is None}
        return out

    def reachable(self):
        """user functions Max compiles: called from the main code, directly or through functions that are compiled.
        A function nobody calls is not checked by Max (probes R207, R319, R443); a call whose result is not used
        still counts (probe R308)"""
        main = [n for n in self.items if n.kind not in ("func", "require")]
        todo, reach = sorted(self.calls_in(main)), set()
        self.compiled_calls = set(todo)
        while todo:
            name = todo.pop()
            self.compiled_calls.add(name)
            if name in reach or name not in self.funcs or self.op_named(name):
                continue
            reach.add(name)
            f = self.funcs[name]
            todo += sorted(self.calls_in(f.body))
            for d in f.defaults.values():
                todo += sorted(c.name for c in d.all_calls() if c.obj is None)
        return reach

    def op_named(self, name):
        """a user function with this name is ignored: the gen operator runs (probes R622, R820, R822). Without the
        Gen reference the built-in name list decides (errors in such a function then only warn)"""
        if name in MEASURED_OP_FUNCS:
            return True
        return self.ref.callable(name) if self.ref else name in FALLBACK_OPS

    def add(self, rule, line, msg, key=None, sev=None):
        if self.lib_ctx is not None and self.in_func is not None:   # a finding inside a require()'d library function
            lib, req, internal = self.lib_ctx
            msg = "in %s() of the require()'d library %s (line %d there): %s" % (self.in_func.name, lib, line, msg)
            if internal and (sev or RULES[rule][0]) == "error":
                sev = "warn"
                msg += ". Only a warn: this library was found only in RNBO's internal folder (G117)"
            key = ("lib", lib, key if key is not None else (line, msg))
            line = req
        k = (rule, key if key is not None else (line, msg))
        sev = sev or RULES[rule][0]
        if rule in EVERY_FUNCTION:
            pass                           # checked in every function body, called or not (probe R1040)
        elif (sev == "error" and self.in_func is not None and len(self.func_defs.get(self.in_func.name, [])) > 1
              and self.func_defs[self.in_func.name][0] is not self.in_func):
            sev = "warn"
            if self.dup_first_measured(self.in_func.name):
                msg += (". Not an error here: %s() is defined more than once, and for calls like the ones here Max ran "
                        "the first definition, not this one (probe R1049); whether it still checks this one was not "
                        "measured" % self.in_func.name)
            else:
                msg += (". Not an error here: %s() is defined more than once, and which definition Max runs for the "
                        "calls here was not measured (probe R1049 measured only a call that fits the first one's "
                        "parameter count and not the other's)" % self.in_func.name)
        elif (sev == "error" and self.in_func is not None and len(self.func_defs.get(self.in_func.name, [])) > 1
              and self.in_func.name in self.reach and not self.dup_first_measured(self.in_func.name)):
            sev = "warn"
            msg += (". Not an error here: %s() is defined more than once, and which definition Max runs for the calls "
                    "here was not measured (probe R1049 measured only a call that fits the first one's parameter count "
                    "and not the other's: the first ran)" % self.in_func.name)
        elif sev == "error" and self.in_func is not None and self.in_func.name not in self.reach:
            sev = "warn"
            if self.op_named(self.in_func.name):
                msg += (". Not an error here: %s() has the name of a gen operator, and Max ran the built-in instead of "
                        "such a function without checking its body (scale, mix, cycle, wrap: probes R622, R820, R822, "
                        "R1053, R1233)" % self.in_func.name)
            else:
                msg += (". Not an error yet: %s() is never called here, and Max checks only the functions that are "
                        "called (probes R207, R319, R443, R1041)" % self.in_func.name)
        # one finding per key, but a more severe one with the same key still counts: a warn from an uncalled
        # function must not hide the same error in the main code or in a called function
        if self.seen.get(k, -1) >= SEV_RANK[sev]:
            return
        self.seen[k] = SEV_RANK[sev]
        self.findings.append({"rule": rule, "sev": sev, "line": line, "msg": msg})

    # ---- scopes
    def visible(self, name):
        return any(name in s for s in self.scopes)

    def define(self, name, line):
        if self.is_constant(name) or (name.isupper() and self.is_constant(name.lower())):
            refused = ("Max 9.2.0 refuses it: \"can't assign to predefined constant '%s'\", then 'main2.lua:727: failed "
                       "to compile genpatcher' at audio start - the gen~ is silent (probes R90-R92, R94, R95)" % name)
            if self.max_version >= (9, 2):
                judged = ("" if self.max_version == (9, 2, 0) else
                          "Judged by the Max 9.2.0 rules: the Max version is not known here" if self.max_version_text == "unknown"
                          else "Max %s was not measured; judged like 9.2.0" % self.max_version_text)
                self.add("G112", line, sentences("'%s' is a predefined Gen constant. %s" % (name, refused), judged,
                                                 "Rename the variable"), key=name)
            else:
                older = ("Accepted by Max 9.1.4" if self.max_version == (9, 1, 4) else
                         "Max 9.1.4 accepted it; Max %s was not measured" % self.max_version_text)
                self.add("G112", line, "'%s' is a predefined Gen constant. %s, but %s. Rename it before updating"
                         % (name, older, refused), key=name, sev="warn")
        if name in self.decls or self.visible(name):
            return
        self.scopes[-1][name] = line
        if name not in ("in", "out"):        # bare in / out are in1 / out1 (probe R954)
            self.check_name(name, line, "variable")

    def dropped_calls(self):
        """main-code assignments 'v = f(...)' where the user function f writes (directly or through another user
        function) and v never reaches an output, a History, a write, a condition or a bare statement. Max drops such a
        call together with its writes (value probes R1537, R1539-R1541, R1543 on Max 9.1.5 and 9.2.0); a used result
        (R1538), a bare call statement (R1542) and a History target (R1544) keep it.
        Sets self._dropped [(node, targets, functions, in_loop)] and self._only_dropped (functions every main-code call
        of which is dropped and that no function calls)."""
        if getattr(self, "_dropped", None) is not None:
            return self._dropped
        self._dropped, self._only_dropped = [], set()
        funcs = {f.name: f for f in self.funcs.values() if getattr(f, "kind", "") == "func"}
        calls, writers = {}, set()
        for name, f in funcs.items():
            cs = [c for x, _ in walk_nodes(f.body, True) for e in node_exprs(x) for c in e.all_calls()]
            calls[name] = {c.name for c in cs if c.obj is None and c.name in funcs}
            if any(is_write(c) for c in cs):
                writers.add(name)
        grow = True
        while grow:
            grow = False
            for name, cs in calls.items():
                if name not in writers and cs & writers:
                    writers.add(name)
                    grow = True
        if not writers:
            return self._dropped

        def walk(items, loop=False):
            for n in items:
                if n.kind == "func":
                    continue
                yield n, loop
                if n.kind == "if":
                    yield from walk(n.then, loop)
                    yield from walk(n.els or [], loop)
                elif n.kind == "for":
                    yield from walk(n.init + n.step + n.body, True)
                elif n.kind == "while":
                    yield from walk(n.body, True)
                elif n.kind == "block":
                    yield from walk(n.body, loop)

        nodes = list(walk(self.items))
        live = {name for name, d in self.decls.items() if d[0] == "History"}
        assigns = []
        for n, _ in nodes:
            if n.kind == "assign":
                ts = [t for t, _ in n.targets]
                rd = {r for r, _ in n.expr.all_reads()}
                if n.op != "=":
                    rd |= set(ts)
                for c in n.expr.all_calls():
                    if is_write(c):
                        for a in c.args + list(c.named.values()):
                            live |= {r for r, _ in a.all_reads()}
                if any(re.fullmatch(r"out\d*", t) for t in ts):
                    live |= rd
                assigns.append((ts, rd))
            else:
                for e in node_exprs(n):
                    live |= {r for r, _ in e.all_reads()}
        grow = True
        while grow:
            grow = False
            for ts, rd in assigns:
                if any(t in live for t in ts) and not rd <= live:
                    live |= rd
                    grow = True
        # measured with functions that return a value (R1537-R1544); a no-return function is G114's case
        valued = {name for name, f in funcs.items()
                  if any(x.kind == "return" and x.expr.toks for x, _ in walk_nodes(f.body, True))}
        main_calls, dropped_calls = {}, {}
        for n, loop in nodes:
            names = [c.name for e in node_exprs(n) for c in e.all_calls()
                     if c.obj is None and c.name in writers and c.name in valued]
            for x in names:
                main_calls[x] = main_calls.get(x, 0) + 1
            if n.kind != "assign" or n.op != "=" or not names:
                continue
            ts = [t for t, _ in n.targets]
            if any(t in live or t in self.decls or re.fullmatch(r"out\d*", t) for t in ts):
                continue
            self._dropped.append((n, ts, sorted(set(names)), loop))
            for x in names:
                dropped_calls[x] = dropped_calls.get(x, 0) + 1
        called_in_funcs = {x for cs in calls.values() for x in cs}
        self._only_dropped = {x for x in writers if main_calls.get(x) and main_calls[x] == dropped_calls.get(x, 0)
                              and x not in called_in_funcs}
        return self._dropped

    def drop_rule(self):
        """G210: a writing user function whose result is never used: Max drops the call and its writes"""
        by_fn = {}
        for n, ts, names, loop in self.dropped_calls():
            for x in names:
                by_fn.setdefault(x, []).append((n.line, ts[0], loop))
        for name, sites in sorted(by_fn.items()):
            line, var, _ = sites[0]
            more = (" (%d calls like this, lines %s)" % (len(sites), ", ".join(str(x) for x in sorted({s[0] for s in sites})))
                    if len(sites) > 1 else "")
            loop = (" A call inside a for or while loop was not measured; judged the same." if any(s[2] for s in sites)
                    else "")
            self.add("G210", line, sentences(
                "%s() writes to a Data, Buffer or Delay, but its result goes to '%s', which never reaches an output, a "
                "History or a write%s. Max drops such a call together with its writes, so nothing is written (value "
                "probes R1537, R1539-R1541, R1543, Max 9.1.5 and 9.2.0)" % (name, var, more), loop,
                "Call it as a statement without keeping the result, %s(...); (that write ran, probe R1542), or use the "
                "result" % name), key=("drop", name))

    def old_max(self):
        """judge by Max 9.1.x: 9.2.0 changed many Gen compiler rules (skills/gen-pitfalls/references/versions.md,
        maxprobe/results914_*.json and results915_22.json)"""
        return self.max_version < (9, 2)

    def version_rules(self):
        """code that Max 9.1.4 refuses and 9.2.0 runs (references/versions.md): error when judging 9.1.x,
        an info for 9.2 (the patch may also have to run on 9.1)"""
        old = self.old_max()
        sev = "error" if old else "info"

        def say(rule, line, fails, probes, fix, key, unsure=False, stage="when audio starts", where=" on 9.1.4",
                measured=((9, 1, 4), (9, 2, 0))):
            unmeasured = self.max_version not in measured and self.max_version_text != "unknown"
            note = (" Max %s was not measured: judged like %s." % (self.max_version_text, "9.1.4" if old else "9.2.0")
                    if unmeasured else "")
            if old:
                msg = "Max %s: %s %s (%s%s). Max 9.2.0 runs it.%s %s" % (
                    self.max_version_text, fails, stage, probes, where, note, fix)
            else:
                msg = "Runs on Max 9.2.0, but Max 9.1.4 refuses it: %s (%s). Only matters if the patch must also run on " \
                      "9.1.%s %s" % (fails, probes, note, fix)
            self.add(rule, line, msg, key=key, sev=("warn" if old else "info") if unsure else sev)

        # a user function with a branch, inside the value of a poke or a Delay write: ?: in a return (results914_17-19,
        # results915_22) or a returned variable set in an if block (results915_22 R1520-R1522, R1529, R1532, R1533)
        funcs = [f for f in self.funcs.values() if getattr(f, "kind", "") == "func"]   # local and require()'d
        tern = {}
        for f in funcs:
            k = branch_kind(f)
            if k:
                tern[f.name] = k
        if tern:
            self.dropped_calls()
            sites = [n for n, infn in walk_nodes(self.items) if not infn]
            for n in self.items:
                # a function whose every call is dropped is not compiled into the gen~: Max runs it (R1535, R1536);
                # G210 says that its writes never happen
                if n.kind == "func" and n.name not in self._only_dropped:
                    sites += [x for x, _ in walk_nodes(n.body, True)]
            for n in sites:
                for e in node_exprs(n):
                    for c in e.all_calls():
                        if c.obj is not None and c.name in ("poke", "write"):
                            vals, rest = c.args[:1], c.args[1:]
                        elif c.obj is None and c.name == "poke":
                            vals, rest = c.args[1:2], c.args[2:]
                        else:
                            continue
                        what = "%s.%s(...)" % (c.obj, c.name) if c.obj else "poke(...)"
                        hv = sorted({x.name for a in vals for x in a.all_calls() if x.obj is None and x.name in tern})
                        hr = sorted({x.name for a in rest + list(c.named.values()) for x in a.all_calls()
                                     if x.obj is None and x.name in tern})
                        if hv:
                            say("G130", c.line, "%s() %s, and is called inside the value written by %s; that fails "
                                "with 'gen2.dsp.Model:1455: assertion failed!'" % (hv[0], tern[hv[0]], what),
                                "probes R1303, R1304, R1332-R1335 on 9.1.4, R1520-R1522, R1524-R1526, R1529-R1534, R1545, "
                                "R1547 on 9.1.5, also in a for loop and inside another user function; a real patch failed "
                                "this way",
                                "Put the result in a variable first, then write that variable: v = %s(x); then the write "
                                "(R1527, R1528 ran on 9.1.5). A function without a branch runs there (R1523)" % hv[0],
                                ("tern", c.line), where="", measured=((9, 1, 4), (9, 1, 5), (9, 2, 0)))
                        elif hr:
                            say("G130", c.line, "%s() %s, and is called inside another argument of %s; inside the "
                                "written value this fails with 'gen2.dsp.Model:1455'" % (hr[0], tern[hr[0]], what),
                                "probes R1303, R1332; other arguments not measured",
                                "Put the result in a variable first", ("tern", c.line), unsure=True)
        # outN that only a function assigns, or a gap in the numbering (results914_6a R76, results914_10 R315)
        main_outs, all_outs, first = set(), set(), {}
        for n, infn in walk_nodes(self.items):
            if n.kind != "assign":
                continue
            for t, tline in n.targets:
                m = re.fullmatch(r"out(\d*)", t)
                if not m:
                    continue
                k = int(m.group(1) or 1)
                all_outs.add(k)
                first.setdefault(k, tline)
                if not infn:
                    main_outs.add(k)
        top = max(all_outs) if all_outs else 0
        missing = top - 1 - len({k for k in main_outs if k < top}) if all_outs else 0
        if top > MAX_OUT_GAPS:
            if missing > 0 or top not in main_outs:
                say("G131", first[top], "out%d is the highest output and %d outputs below it are not assigned in the "
                    "main code; Max prints 'out: variable expr_N is not defined' for such a gap" % (top, missing),
                    "probes R76, R315", "Check the output number (a typo?) and assign every output from out1 up",
                    ("outgap", "high"))
        elif all_outs:
            gaps = [k for k in range(1, max(all_outs) + 1) if k not in main_outs]
            for k in gaps:
                line = first.get(k, max(first.values()))
                why = ("out%d is assigned only inside a function" % k if k in all_outs
                       else "out%d is never assigned, but a higher output is" % k)
                say("G131", line, "%s; Max prints 'out: variable expr_N is not defined'" % why, "probes R76, R315",
                    "Assign out%d in the main code (out%d = 0; is enough)" % (k, k), ("outgap", k))
        # a function from a library that another library requires (nested require: results914_20 R1401)
        done = set()
        for n, _ in walk_nodes(self.items):
            for e in node_exprs(n):
                for c in e.all_calls():
                    f = self.funcs.get(c.name) if c.obj is None else None
                    via = getattr(f, "nested", None) if f is not None else None
                    if via and c.name not in done:
                        done.add(c.name)
                        say("G133", c.line, "%s() comes from %s, which %s requires (a nested require); Max prints "
                            "'operator %s not defined'" % (c.name, f.lib, via, c.name), "probe R1401",
                            "require %s directly in the codebox" % os.path.splitext(f.lib)[0], ("nested", c.name),
                            stage="at load")
        # an empty for body (results914_6a R82)
        for n, _ in walk_nodes(self.items):
            if n.kind == "for" and all(x.kind == "empty" for x in n.body):
                say("G132", n.line, "a for loop with an empty body fails", "probe R82",
                    "Remove the loop or give it a body", ("emptyfor", n.line))

    def is_constant(self, name):
        return name in MEASURED_CONSTANTS or bool(self.ref and self.ref.constant(name))

    def check_name(self, name, line, what):
        if not self.ref:
            return
        if name in self.ref.ops:
            self.add("G303", line, "%s '%s' has the name of the gen operator %s()" % (what, name, name), key=name)
        else:
            low = {k.lower(): k for k in self.ref.ops}
            if name.lower() in low:
                self.add("G304", line, "%s '%s' differs from gen operator '%s' only by case" % (what, name, low[name.lower()]), key=name)

    def push(self):
        self.scopes.append({})

    def pop(self, plain=False):
        for name, line in self.scopes.pop().items():
            if name not in self.dead:
                self.dead[name] = line
                if plain:
                    self.dead_plain.add(name)    # first assigned in a { } block without if/for/while

    # ---- main
    def main_flow(self):
        """MainFlow of the main code, or None if it failed (then G102 / G103 only warn)"""
        decl_kind = {}
        for n, in_func in walk_nodes(self.items):
            if n.kind == "decl" and not in_func:
                for it in n.items:
                    decl_kind.setdefault(it[0], n.kw)
        memo = {}

        def effects(name):
            """2: the function body pokes (probe R1072), 1: other side effects, 0: none"""
            if name not in memo:
                measured, other = self.body_effects(self.funcs[name])
                memo[name] = 2 if "poke" in measured else 1 if measured or other else 0
            return memo[name]
        try:
            return MainFlow(self.items, decl_kind, lambda name: name in self.funcs and not self.op_named(name),
                            effects, self.abstractions, self.ref, self.old_max())
        except RecursionError:
            raise
        except Exception as e:  # never let it stop the other checks
            self.add("G400", 0, "the block and liveness analysis failed (internal error %s, please report it); "
                     "G102 and G103 only warn here" % type(e).__name__, sev="warn")
            return None

    def run(self):
        self.scopes, self.dead, self.dead_plain = [{}], {}, set()
        self.in_func = None
        self.block_depth = self.loop_depth = 0
        self.flow = self.main_flow()
        self.pending = {}                # (rule, name) -> finding: the most severe one per name is kept
        seen_expr = None
        first_stmt = None
        first_item = None
        for n in self.items:
            if is_require(n):
                if first_item is not None:
                    what, line = first_item
                    self.add("G118", n.line, "require(\"%s\") comes after the %s at line %d. Every require must come "
                             "first. Max: %s" % (n.lib, what, line,
                                                 "the gen~ fails to compile (probe R322)" if what == "function"
                                                 else "'operator require not defined' (probe R226)"))
                if n.nosemi:
                    self.add("G116", n.line, "require has no ';' after it. Works in Max 9.2.0 (probes R142, R184); "
                             "adding ';' is cleaner")
                continue                     # require("lib") comes first (published packages, Cycling '74 code)
            if first_item is None:
                first_item = ({"func": "function", "decl": "declaration"}.get(n.kind, "statement"), n.line)
            if n.kind == "func" and first_stmt is not None:
                if first_stmt.kind == "empty":
                    self.add("G111", n.line, "function %s() is defined after the empty statement ';' at line %d (an extra "
                             "';', e.g. '};' after a function body, counts as a statement). Max: 'function definitions not "
                             "allowed here (function definitions must precede all statements)' (probe R227). Remove that "
                             "';'" % (n.name, first_stmt.line))
                else:
                    self.add("G111", n.line, "function %s() is defined after line %d. Max: 'function definitions not "
                             "allowed here (function definitions must precede all statements)' (probe P-07)"
                             % (n.name, first_stmt.line))
            elif n.kind != "func" and first_stmt is None:
                first_stmt = n                 # an empty statement ';' counts too (probe R227)
            if n.kind == "decl":
                if seen_expr is not None:
                    self.decl_after(n, seen_expr, "")
                self.decl(n)
            elif n.kind != "func" and seen_expr is None:
                seen_expr = n                  # an empty statement ';' counts too (probes R460, R693)
        for n in self.items:
            if n.kind == "func" and n.name == "pass":
                called = n.name in self.compiled_calls
                self.add("G206", n.line, "a user function named pass %s: Max printed no message for the codebox, only "
                         "'main2.lua:727: failed to compile genpatcher' (probe R821, where it was called). Rename it"
                         % ("fails to compile" if called else "is not called here, which runs (probe R1054), but it "
                            "failed to compile when called"),
                         key=("opfn", n.name), sev="error" if called else "warn")
            elif n.kind == "func" and self.func_defs[n.name][0] is not n:
                first = self.func_defs[n.name][0]
                if self.dup_first_measured(n.name):
                    what = ("For a call that fits the first one's parameter count and not this one's, Max 9.1.4 and "
                            "9.2.0 ran the first definition, not this one (probe R1049)")
                else:
                    what = ("Max 9.1.4 and 9.2.0 ran the first definition for a call that fits the first one's "
                            "parameter count and not the other's (probe R1049); which one runs for the calls here was "
                            "not measured")
                self.add("G209", n.line, "function %s() is defined again (first at line %d). %s. Rename one of them"
                         % (n.name, first.line, what), key=("dupfn", n.line))
            elif n.kind == "func" and n.name in self.lib_replaced:
                self.add("G207", n.line, "%s() replaces the function of the same name from the require()'d library: the "
                         "local one runs (probe R623)" % n.name, key=("libfn", n.name))
            if n.kind == "func" and n.name != "pass" and self.op_named(n.name):
                if n.name in MEASURED_OP_FUNCS:
                    what = ("Max ignores the user function, also its body, and runs the built-in %s() (probe%s %s)"
                            % (n.name, "s" if "," in MEASURED_OP_FUNCS[n.name] else "", MEASURED_OP_FUNCS[n.name]))
                else:
                    what = ("For scale, mix, cycle and wrap Max ignored the user function and ran the built-in (probes "
                            "R622, R820, R822, R1233); for %s() this was not measured" % n.name)
                self.add("G206", n.line, "user function %s() has the name of a gen operator. %s. Rename it"
                         % (n.name, what), key=("opfn", n.name))
        for n in self.items:
            if n.kind == "decl":
                self.cur_node = n
                self.check_exprs(n)
            elif n.kind == "func":
                self.function(n)
            else:
                self.stmt(n)
        self.flush_pending()
        self.output_paths()
        self._dropped = None
        self.version_rules()
        self.drop_rule()
        local = {n.name for n in self.items if n.kind == "func"}
        for name in sorted(self.reach - local):
            # a called function of a require()'d library is compiled like a local one: a no-return one fails when
            # called (probe R208), and library and local functions share one namespace (probe R623)
            f = self.funcs[name]
            self.lib_ctx = (getattr(f, "lib", ""), getattr(f, "req_line", 0), getattr(f, "internal", False))
            try:
                self.function(f)
            finally:
                self.lib_ctx = None
        return self.findings

    def output_paths(self):
        """G128: an output assigned only inside an if (not on every path) is 0 for a sample where that code does not
        run, also after it ran earlier: it does not keep its last value (probes R814, R815). Outputs assigned in a
        loop body or in a function are left alone"""
        main = [n for n in self.items if n.kind not in ("func", "require")]
        first, skip, ifs = {}, set(), {}

        def norm(t):
            return "out1" if t == "out" else t

        def scan(stmts, loop, if_line):
            for n in stmts:
                if n.kind == "assign":
                    for t, line in n.targets:
                        if OUT_NAME.match(norm(t)):
                            first.setdefault(norm(t), line)
                            ifs.setdefault(norm(t), []).append(if_line)
                            if loop:
                                skip.add(norm(t))
                elif n.kind == "if":
                    scan(n.then, loop, if_line or n.line)
                    scan(n.els or [], loop, if_line or n.line)
                elif n.kind == "for":
                    scan(n.init, loop, if_line)
                    scan(n.body + n.step, True, if_line)
                elif n.kind == "while":
                    scan(n.body, True, if_line)
                elif n.kind == "block":
                    scan(n.body, loop, if_line)

        def everywhere(stmts, name):
            for n in stmts:
                if n.kind == "assign" and any(norm(t) == name for t, _ in n.targets):
                    return True
                if n.kind == "if" and n.els is not None and everywhere(n.then, name) and everywhere(n.els, name):
                    return True
                if (n.kind == "block" and everywhere(n.body, name)) or (n.kind == "for" and everywhere(n.init, name)):
                    return True
            return False
        scan(main, False, None)
        for f in self.items:
            if f.kind == "func":
                for x, _ in walk_nodes(f.body, True):
                    if x.kind == "assign":
                        skip |= {norm(t) for t, _ in x.targets}
        for name, line in sorted(first.items()):
            if name in skip or None in ifs[name] or everywhere(main, name):
                continue
            where = sorted(set(ifs[name]))
            self.add("G128", line, "%s is assigned only inside %s, not on every path. In a sample where that code does "
                     "not run, %s is 0; it does not keep its last value (probes R814, R815). If it should hold, keep the "
                     "value in a History and assign %s on every path"
                     % (name, "the if at line %d" % where[0] if len(where) == 1 else
                        "the ifs at lines %s" % ", ".join(map(str, where[:4])), name, name), key=("outpath", name))

    def decl_after(self, n, first, where):
        if first.kind == "empty":
            self.add("G101", n.line, "%s%s declared after the empty statement ';' at line %d (it counts as an expression). "
                     "Max: 'declarations must come before any expressions' (probes R460, R693). Remove that ';'"
                     % (where, n.kw, first.line))
        else:
            self.add("G101", n.line, "%s%s declared after the first expression (line %d). Max: 'declarations must come "
                     "before any expressions' (%s)" % (where, n.kw, first.line, "probe R209; also in a function that is never "
                                                                       "called, probe R1040" if where else "probes R40, P-15"))

    def block_order(self, body, func_body=False):
        """declarations must come first in a function body (probe R209) and in an if/for/while block: first in a
        block works (probe R225), after a statement there it fails (probe R1006)"""
        first = None
        for s in body:
            if s.kind != "decl":
                first = first or s
            elif first is not None:
                if func_body:
                    self.decl_after(s, first, "in %s(): " % self.in_func.name)
                else:
                    self.add("G101", s.line, "%s declared after the statement at line %d in the same block. Max 9.1.4 "
                             "and 9.2.0 refuse the codebox (probe R1006); first in a block it works (probe R225). Move it "
                             "to the top of the block" % (s.kw, first.line), key=("blockdecl", s.line))

    def lower_kw(self, n):
        if not getattr(n, "lower", None):
            return
        if n.lower == "delay":
            self.add("G119", n.line, "'delay %s(...)' is not a declaration: write 'Delay %s(...)'. Max: \"The delay() "
                     "operator is not supported in GenExpr; use the Delay.read and Delay.write instead.\" (probe R982)"
                     % (n.items[0][0], n.items[0][0]), key=n.line)
        else:
            self.add("G119", n.line, "'%s' must be written '%s'. Max: \"unrecognized declaration type %s\" when audio "
                     "starts (probe %s)" % (n.lower, n.kw, n.lower, LOWER_DECL_PROBE[n.lower]), key=n.line)

    def decl(self, n):
        self.lower_kw(n)
        for name, line, args, named in n.items:
            if name in self.decls:
                self.add("G301", line, "'%s' is declared twice (first line %d). Max merges them silently" % (name, self.decls[name][1]), key=name)
                continue
            self.decls[name] = (n.kw, line, args, named)
            if self.ref and name in self.ref.ops:
                if n.kw == "Param":
                    self.add("G303", line, "Param '%s' has the name of the gen operator %s() (known to compile as a Param)" % (name, name), key=name)
                else:
                    self.check_name(name, line, n.kw)
            elif self.ref:
                self.check_name(name, line, n.kw)
            if self.old_idents is not None and name not in self.old_decls and name in self.old_idents:
                self.add("G302", line, "new %s '%s' reuses a name that the old version already used as a variable" % (n.kw, name), key=name)
            if n.kw == "Param":
                self.param(name, line, args, named)
                if name in self.patcher_params and not args and not named:
                    # 'Param gain;' with no value: the documented way to use the patcher's [param gain] in a codebox
                    self.add("G415", line, "Param '%s' has no value here and names a param of the gen patcher: it uses "
                             "the patcher param (its value wins, probe R635)" % name, key=("pparam", name), sev="info")
                elif name in self.patcher_params:
                    self.add("G415", line, "Param '%s' has the same name as a param of the gen patcher. Max uses the "
                             "patcher param's value, not this declaration's (probe R635: [param gainx 3] beat Param "
                             "gainx(5)). Rename one of them, or drop this declaration" % name, key=("pparam", name))
            if n.kw == "Buffer" and args and not (len(args[0].toks) == 1 and args[0].toks[0].kind == "str"):
                self.add("G115", line, "Buffer %s(%s): the buffer~ name must be in quotes. Max: 'variable %s is not "
                         "defined' when audio starts (probe R79)" % (name, args[0].text(), args[0].text()), key=("buf", name))

    def param(self, name, line, args, named):
        for k in named:
            if k not in ("min", "max", "default", "name"):
                if self.old_max():
                    self.add("G113", line, "Param '%s': '%s' is not a Param attribute (min, max, default, name). Max %s: the "
                             "gen~ fails when audio starts (probe R78 on 9.1.4); Max 9.2.0 only warns" % (
                                 name, k, self.max_version_text), key=(name, k), sev="error")
                else:
                    self.add("G113", line, "Param '%s': '%s' is not a Param attribute (min, max, default, name). Max 9.2.0 "
                             "warns \"%s is not a valid attribute of Param\" (the setting is probably ignored); Max 9.1.4 "
                             "refuses the code (probe R78)" % (name, k, k), key=(name, k))
        dflt = num_value(args[0]) if args else 0.0
        if "min" not in named or "max" not in named:
            miss = " and ".join(k for k in ("min", "max") if k not in named)
            if dflt is not None and not (0.0 <= dflt <= 1.0):
                self.add("G407", line, "Param '%s' has no %s but its default %g is outside 0..1. Max itself keeps the "
                         "value (probe R1106: Param big(5) reads 5), but exported code (exportcode, Oopsy) uses 0..1 and "
                         "clips it. Give min and max if the code is exported" % (name, miss, dflt), key=name)
            else:
                self.add("G412", line, "Param '%s' has no %s: exported code (exportcode, Oopsy) treats it as 0..1" % (name, miss), key=name)
        mx = num_value(named["max"]) if "max" in named else None
        mn = num_value(named["min"]) if "min" in named else None
        if dflt is not None and mx is not None and dflt > mx and (mn is None or mn <= mx):
            self.add("G414", line, "Param '%s' starts at %g, above its max %g: Max starts it at %g (probe R644)"
                     % (name, dflt, mx, mx), key=("init", name))
        elif dflt is not None and mn is not None and dflt < mn and (mx is None or mn <= mx):
            self.add("G414", line, "Param '%s' starts at %g, below its min %g: Max starts it at %g (probe R1101)"
                     % (name, dflt, mn, mn), key=("init", name))
        if mx is not None and mx >= 0.97 and re.search(r"fb|feedback|fbk|decay|regen", name, re.I):
            exprs = [e for x, _ in walk_nodes(self.items) for e in node_exprs(x)]
            if any(reads_outside(e, name, BOUNDED_CALLS | TIME_PITCH_CALLS) for e in exprs):
                self.add("G410", line, "Param '%s' max=%g: loop gain near 1 can ring for a long time (+30 dB on "
                         "matching input)" % (name, mx), key=name)
            elif any(reads_outside(e, name, TIME_PITCH_CALLS) for e in exprs):
                self.add("G410", line, "Param '%s' max=%g: loop gain near 1 can ring for a long time. Its level stays "
                         "bounded: every use is inside sin, tanh, clamp or a similar function" % (name, mx), key=name)

    def function(self, n):
        saved_decls = dict(self.decls)      # History declared inside a function belongs to that function
        self.main_decls = saved_decls
        self.decls = {}                     # the main code's History, Param, Data are not visible (probes R201, R202, R314)
        self.scopes, self.dead, self.dead_plain = [{p: n.line for p in n.params}], {}, set()
        self.in_func = n
        self.block_depth = self.loop_depth = 0
        self.flocals = set(n.params)
        self.fdefs, self.fread = {}, set()  # assignment lines and read names inside this function
        for x, _ in walk_nodes(n.body, True):
            if x.kind == "assign":
                for name, line in x.targets:
                    self.fdefs.setdefault(name, []).append(line)
            for e in node_exprs(x):
                self.fread |= {r for r, _ in e.all_reads()}
        self.return_check(n, n.line, "function %s()" % n.name)
        self.default_values(n)
        self.block_order(n.body, func_body=True)
        for s in n.body:
            self.stmt(s)
        clash = sorted(x for x in self.flocals if x in self.top_names) if self.lib_ctx is None else []
        for x in clash:
            self.add("G203", n.line, "in %s(): '%s' is also a name in the main code. Runs in Max 9.2.0 (probe P-06, audio on)" % (n.name, x), key=(n.name, x))
        self.scopes, self.dead, self.dead_plain = [{}], {}, set()
        self.in_func = None
        self.decls = saved_decls

    def calls_of(self, name):
        """plain calls name(...) in the code Max compiles: the main code, the called functions and their defaults"""
        if getattr(self, "_compiled_exprs", None) is None:
            main = [n for n in self.items if n.kind not in ("func", "require")]
            bodies = [main] + [self.funcs[x].body for x in sorted(self.reach) if x in self.funcs]
            exprs = [e for x in sorted(self.reach) if x in self.funcs for e in self.funcs[x].defaults.values()]
            for nodes in bodies:
                for x, _ in walk_nodes(nodes, True):
                    exprs += node_exprs(x)
            self._compiled_exprs = exprs
        return [c for e in self._compiled_exprs for c in e.all_calls() if c.obj is None and c.name == name]

    def default_used(self, f, p):
        """does a call of f in the code Max compiles leave parameter p out, so that the default is used?"""
        idx = f.params.index(p) if p in f.params else 0
        return any(len(c.args) <= idx and p not in c.named for c in self.calls_of(f.name))

    def dup_first_measured(self, name):
        """name is defined more than once: is every call the measured form? R1049 called uf with as many arguments
        as the first definition has parameters and the second has not: the first ran (12). With that probe, 'the
        first runs' and 'the one whose parameter count fits runs' give the same result, so other calls (an argument
        count that fits a later definition, or definitions with the same count) were not measured"""
        defs = self.func_defs.get(name, [])
        if len(defs) < 2:
            return True
        k = len(defs[0].params)
        later = {len(d.params) for d in defs[1:]}
        return all(len(c.args) == k and not c.named and k not in later for c in self.calls_of(name))

    def default_values(self, n):
        """names and calls in parameter defaults, uf(a, b = VOICE): a call that leaves b out uses the default (probes
        R180, R181, R628). Measured: the upper-case VOICE and bare noise fail when a call leaves the argument out
        (R1213, R1214); when every call passes it, or for the other forms, it warns"""
        for p, e in n.defaults.items():
            where = "the default value of %s in %s()" % (p, n.name)
            note = "Constant defaults work (probes R180, R181, R628); this form was not measured"
            # every compiled call passes p: the default is never used, and whether Max checks it then was not measured
            passed = False                   # Max checks the default even when every call passes p (R1470, R1471)
            unused = ""
            for name, line in e.all_reads():
                if (name in n.params or name in EXTRA_BARE or name in GLOBALS or self.is_constant(name) or
                        (self.ref and self.ref.bare_ok(name))):
                    continue
                low = name.lower()
                if name.isupper() and (low in GLOBALS or (self.ref and low in self.ref.ops and
                                                          self.ref.ops[low]["cat"] == "global")):
                    self.add("G125", line, sentences(
                        "%s reads '%s', which does not exist: the Gen global is '%s'. Max 9.1.4 and 9.2.0 refuse it when "
                        "the function is called, even when every call passes that argument (probes R1213, R1470; in the main code: 'variable %s is not "
                        "defined', probes R171, R335)" % (where, name, low, name), unused, "Write %s" % low),
                        key=("dflt", n.name, p, name), sev="warn" if passed else None)
                elif name.isupper() and (self.is_constant(low) or (self.ref and self.ref.bare_ok(low))):
                    continue
                elif (self.ref and self.ref.callable(name)) or name in MEASURED_BARE_FAIL:
                    self.add("G108", line, sentences(
                        "%s is the gen operator '%s' without (). Max 9.1.4 and 9.2.0 refuse it when the function is "
                        "called without that argument (probe R1214, measured for noise; in the main code: 'variable %s "
                        "is not defined', probe P-11)" % (where, name, name),
                        unused if name in MEASURED_BARE_FAIL else
                        "Only a warn: '%s' may be a param of the gen patcher, and what a default can see was not "
                        "measured" % name, "Write %s()" % name),
                        key=("dflt", n.name, p, name), sev=None if name in MEASURED_BARE_FAIL and not passed else "warn")
                elif name in self.funcs:
                    self.add("G108", line, "%s is the user function '%s' without (). %s" % (where, name, note),
                             key=("dflt", n.name, p, name), sev="warn")
                elif re.fullmatch(r"(in|out)\d*", name) or name in self.patcher_params:
                    self.add("G205", line, "%s reads '%s'. A function body cannot see an inlet (probe R210); what a "
                             "default can see was not measured. %s" % (where, name, note),
                             key=("dflt", n.name, p, name), sev="warn")
                else:
                    self.add("G104", line, "%s reads '%s', which is not defined %s. %s; a function cannot see the main "
                             "code's names (probe R200)" % (where, name, "in the function" if name in self.top_names
                                                            or name in self.main_decls else "in this codebox", note),
                             key=("dflt", n.name, p, name), sev="warn")
            for c in e.all_calls():
                if c.obj is not None or c.name in self.funcs or c.name in self.abstractions:
                    continue
                if c.name in NOT_CALLABLE:
                    self.add("G109", c.line, "%s calls %s(), which is not a GenExpr function (history(): probe P-12). %s"
                             % (where, c.name, note), key=("dflt", n.name, p, c.name), sev="warn")
                elif self.ref and not self.ref.callable(c.name) and not getattr(self, "missing_libs", None):
                    self.add("G105", c.line, "%s calls %s(), which is not a Gen operator or a user function in this "
                             "codebox" % (where, c.name), key=("dflt", n.name, p, c.name))

    def body_effects(self, f):
        """(measured, other) side effects in a function body. With a poke (also inside an if block: probe R1045), a
        write to its own History or an outN assignment a no-return function compiles on Max 9.2.0 and gives 0 (probes
        R316, R440, R441, R444, R624, R1051); the other effects were not measured"""
        hist = set()
        for x, _ in walk_nodes(f.body, True):
            if x.kind == "decl" and x.kw == "History":
                hist |= {it[0] for it in x.items}
        measured, other = set(), set()
        top = {id(x) for x in f.body}       # History and outN writes: measured only at the top of the body
        for x, _ in walk_nodes(f.body, True):
            if x.kind == "assign":
                for name, _ in x.targets:
                    if name in hist:
                        (measured if id(x) in top else other).add("History write" if id(x) in top else
                                                                  "History write inside a block")
                    elif re.fullmatch(r"out\d*", name):
                        (measured if id(x) in top else other).add("%s =" % name if id(x) in top else
                                                                  "%s = inside a block" % name)
            for e in node_exprs(x):
                for c in e.all_calls():
                    if c.obj is None and c.name == "poke":
                        measured.add("poke")
                    elif c.obj is None and c.name == "splat":
                        other.add("splat()")
                    elif c.obj is not None and c.name in ("poke", "write"):
                        other.add("%s.%s()" % (c.obj, c.name))
                    elif c.obj is None and c.name in self.funcs and c.name != f.name:
                        other.add("%s()" % c.name)
        return measured, other

    def call_sites(self, name):
        """calls of user function name in the code Max compiles (main code and called functions of this codebox):
        (lines of calls written as a statement, lines of calls whose value is used, lines of calls whose value only
        goes into a variable that is never read)"""
        decls = self.main_decls if self.in_func is not None else self.decls
        scopes = [([n for n in self.items if n.kind not in ("func", "require")], self.read_names,
                   {k for k, v in decls.items() if v[0] == "History"})]
        for f in self.items:
            if f.kind == "func" and f.name in self.reach:
                reads, hist = set(), set()
                for x, _ in walk_nodes(f.body, True):
                    for e in node_exprs(x):
                        reads |= {r for r, _ in e.all_reads()}
                    if x.kind == "decl" and x.kw == "History":
                        hist |= {it[0] for it in x.items}
                scopes.append((f.body, reads, hist))
        stmt, used, unread = [], [], []
        # main-code assignments whose value no used statement reads (y = uf(x); z = y * 2; with z never used)
        unused = set()
        if self.flow is not None:
            f = self.flow
            live = {d for u in f.uses.values() if f.level_of(u)[0] for d in u.rd}
            for x, infn in walk_nodes(scopes[0][0]):
                if not infn and x.kind == "assign":
                    ds = [f.def_of.get((id(x), i)) for i in range(len(x.targets))]
                    if all(d is not None and d not in live and not OUT_NAME.match(d.name) and
                           f.decl_kind.get(d.name) != "History" for d in ds):
                        unused.add(id(x))
        for nodes, reads, hist in scopes:
            for x, _ in walk_nodes(nodes):
                calls = [c for e in node_exprs(x) for c in e.all_calls() if c.obj is None and c.name == name]
                if not calls:
                    continue
                if id(x) in unused:
                    unread += [c.line for c in calls]
                    continue
                if (x.kind == "expr" and len(x.expr.calls) == 1 and x.expr.calls[0] is calls[0]
                        and calls[0].start == 0 and calls[0].end == len(x.expr.toks) - 1):
                    stmt.append(calls[0].line)
                elif x.kind == "assign" and not any(t in reads or t in hist or re.fullmatch(r"out\d*", t)
                                                    for t, _ in x.targets):
                    unread += [c.line for c in calls]
                else:
                    used += [c.line for c in calls]
        return stmt, used, unread

    def return_check(self, f, line, what):
        """G114: return statements of a user function (or of a require()'d library function: what names it).
        Max checks them only when the function is called (probes R144, R207, R443)"""
        if self.op_named(f.name):
            return                         # Max runs the built-in instead (G206)
        rets = [x for x, _ in walk_nodes(f.body, True) if x.kind == "return"]
        called = f.name in self.reach
        key = ("noret", f.name)
        if rets:
            empty = [x for x in rets if not x.expr.toks]
            if not empty:
                return                     # a return on some paths only is fine; the other paths give 0 (R204, R626)
            if not called:
                self.add("G114", line, "%s has 'return;' without a value. Not called here, which is fine (probe R443); "
                         "calling it fails (probes R206, R318). Write return 0;" % what, key=key, sev="info")
            elif len(empty) == len(rets):
                self.add("G114", line, "%s has only 'return;' without a value. Calling it fails when audio starts, also "
                         "as a statement: 'gen2.Module:%s attempt to index local 'I' (a nil value)' (probes R206, "
                         "R318). Write return 0; (or the value)" % (what, "2392" if self.old_max() else "2556"), key=key)
            else:
                self.add("G114", line, "%s mixes 'return;' without a value with 'return value;'. Max 9.1.4 and 9.2.0 "
                         "run it (probe R1048, the value path); what the 'return;' path gives was not measured (a "
                         "function with only 'return;' fails when called: probes R206, R318). Write return 0;" % what,
                         key=key, sev="warn")
            return
        if not called:
            self.add("G114", line, "%s has no return. Not called here (or only from functions nobody calls), which is "
                     "fine (probes R144, R207); calling it fails unless its body pokes or writes a History (probes "
                     "R145, R316)" % what, key=key, sev="info")
            return
        measured, other = self.body_effects(f)
        stmt, used, unread = self.call_sites(f.name)
        effects = " and ".join(effect_words(x) for x in sorted(measured | other))
        if self.old_max():                 # Max 9.1.4 judges no-return functions almost the other way round
            if not stmt and not used:      # every call's result goes into a variable that is never read
                if measured - {"History write"} or other:
                    self.add("G114", line, "%s has no return and its body has %s; its result is never used. Max %s "
                             "drops such a call when the body only writes a History or does nothing (probes R73, R145, "
                             "R208, R1046, R1232 on 9.1.4); for this body that was not measured, and calling it for its "
                             "value or as a statement fails (probes R316, R440). Add return with a value"
                             % (what, effects, self.max_version_text), key=key, sev="warn")
                else:
                    self.add("G114", line, "%s has no return; its result is never used, so Max %s drops the call and "
                             "runs (probes R73, R145, R208, R1046, R1232 on 9.1.4). Max 9.2.0 refuses some of these "
                             "(probe R145): add return with a value" % (what, self.max_version_text), key=key,
                             sev="info")
            elif measured:
                if measured & {"poke", "History write"}:
                    # console text recorded for R316, R440-R444, R624 (results914_10-12), not for R1045 (round 16)
                    fails = ("calling it fails when audio starts (probes R316, R440, R441, R444, R624, R1045 on 9.1.4; "
                             "for R316, R440-R442, R444 and R624 the console showed 'gen2.dsp.Model:1455: assertion failed!' "
                             "or ':1703: attempt to index a nil value')")
                else:
                    # only an outN assignment: R1051 failed on 9.1.4, its console text was not recorded
                    fails = ("calling it fails when audio starts (probe R1051 on 9.1.4; its console text was not "
                             "recorded. An output assigned in a function gave 'out: variable expr_N is not defined', "
                             "probe R315)")
                self.add("G114", line, "%s has no return and its body has %s. Max %s: %s. %s. Add return with a value"
                         % (what, effects, self.max_version_text, fails,
                            "Max 9.2.0 refuses it too: the result of a function that writes a History is used as a "
                            "value (probes R625, R1047)" if "History write" in measured and used else
                            "Max 9.2.0 runs it"), key=key)
            elif other:
                self.add("G114", line, "%s has no return and its body has %s. Not measured on Max %s; a no-return "
                         "function that pokes, writes a History or assigns an output fails there when it is called "
                         "(probes R316, R440, R624, R1051). Add return with a value"
                         % (what, effects, self.max_version_text), key=key, sev="warn")
            elif stmt:
                self.add("G114", line, "%s has no return and is called as a statement (line %d). Max %s: fails when "
                         "audio starts (probes R317, R442 on 9.1.4 and 9.2.0). Add return with a value"
                         % (what, min(stmt), self.max_version_text), key=key)
            else:
                self.add("G114", line, "%s has no return; its result is used at line %d. Max %s: fails when audio "
                         "starts (probe R1234 on 9.1.4 and 9.2.0; when the result is never used 9.1.4 drops the call and "
                         "runs, probes R73, R145). Add return with a value" % (what, min(used), self.max_version_text),
                         key=key)
            return
        pokes = measured & {"poke"}
        if not measured and not other:
            self.add("G114", line, "%s has no return, and its body has no poke or History write. Calling it fails when "
                     "audio starts, also as a statement: 'gen2.passes.Type:424: attempt to index local JS (a nil "
                     "value)' (probes R317, R442, R515, R1234; the text is from R442). Add return with a value" % what, key=key)
        elif not measured:
            self.add("G114", line, "%s has no return; its body has %s. Not measured: a no-return function compiles "
                     "when it pokes or writes a History (probes R316, R441) and fails when it does neither (probe R145). "
                     "Add return with a value" % (what, ", ".join(sorted(other))), key=key, sev="warn")
        elif "History write" in measured and used:
            self.add("G114", line, "%s has no return and writes a History; its result is used as a value at line %d. "
                     "Max: C compile error 'expected expression' when audio starts (probe R625; with a poke as well "
                     "it fails too, probe R1047). Add return with a value" % (what, min(used)), key=key)
        elif "History write" in measured and unread and pokes:
            self.add("G114", line, "%s has no return; it pokes and writes a History, and its result goes into a "
                     "variable at line %d that is never read. Not measured for this body: with the result used it fails "
                     "(probe R1047), with a History write alone and the result unread it runs (probe R1046). Add "
                     "return with a value" % (what, min(unread)), key=key, sev="warn")
        elif used and not pokes and "History write" not in measured:
            self.add("G114", line, "%s has no return and its body has %s; its result is used at line %d. Not "
                     "measured for this body: a no-return function that pokes gives 0 (probes R440, R624), one that "
                     "writes a History fails as a value (probe R625). Add return with a value"
                     % (what, effects, min(used)), key=key, sev="warn")
        else:
            self.add("G114", line, "%s has no return. It compiles because its body has %s, and its result is 0 "
                     "(probes R316, R440, R441, R624, R1045, R1046, R1051). Add return with a value if one is meant"
                     % (what, " and ".join(effect_words(x) for x in sorted(measured))), key=key, sev="info")

    def stmt(self, n):
        k = n.kind
        if self.in_func is None:
            self.cur_node = n
        if k == "decl":
            self.lower_kw(n)
            self.check_exprs(n)
            for name, line, args, named in n.items:
                if name not in self.decls:
                    self.decls[name] = (n.kw, line, args, named)
        elif k == "assign":
            self.expr(n.expr)
            self.multi_assign(n)
            for name, line in n.targets:
                if self.in_func is None and re.fullmatch(r"in\d*", name):
                    self.inlet_assign(n, name, line)
                elif self.decls.get(name, (None,))[0] == "Param" and not self.visible(name):
                    self.add("G121", line, "'%s' is a Param and cannot be assigned in the code. Max: \"can't assign to "
                             "parameter %s\" (probe R701; in a function on 9.1.4 and 9.2.0 too, probe R1010). Use another "
                             "variable: %s2 = ...;" % (name, name, name), key=("param", name))
                elif (self.in_func is None and name in self.patcher_params and name not in self.decls
                      and not self.visible(name)):
                    self.add("G121", line, "'%s' is a param of the gen patcher (--param). Max 9.1.4 and 9.2.0 accept "
                             "the assignment: from there on this codebox reads the assigned value, not the param (probe "
                             "R1100: rate = 2 read 2 with [param rate 7]). Assigning a codebox Param fails (\"can't "
                             "assign to parameter %s\", probe R701). Use another variable: %s2 = ...;"
                             % (name, name, name), key=("param", name), sev="warn")
                if n.op != "=":
                    unread = name not in (self.read_names if self.in_func is None else self.fread)
                    if not self.visible(name) and name not in self.decls and unread and self.in_func is None:
                        self.pend("G103", name, line, "warn", "'%s' but '%s' is not assigned before it and is never "
                                  "read. Max 9.2.0 accepts this: it drops the unused statement (probes R140, R302). If "
                                  "you meant to use it, assign it first"
                                  % (short("%s %s %s" % (name, n.op, pretty(n.expr)), 50), name))
                    elif not self.visible(name) and name not in self.decls and unread:
                        self.add("G103", line, "'%s %s ...' in %s(), but '%s' is never assigned before it. Inside a "
                                 "function Max 9.1.4 and 9.2.0 refuse this even when the value is never used (probe "
                                 "R1050; in the main code it is dropped, probe R140). Assign it first, e.g. %s = 0;"
                                 % (name, n.op, self.in_func.name, name, name), key=(self.in_func.name, name))
                    else:
                        self.read(name, line, ("compound", id(n), name))
                if self.in_func is not None:
                    self.flocals.add(name)
                self.define(name, line)
        elif k in ("expr", "return"):
            self.expr(n.expr)                # a return outside a function is a parse error (probe R1205)
            if (k == "expr" and self.in_func is None and not getattr(n, "implicit", False)
                    and self.no_effect(n.expr)):
                if self.silent_box():
                    self.add("G122", n.line, "this codebox assigns no output and writes nothing, so the value of this "
                             "expression goes nowhere: 'cos(in1);' compiles and out1 stays 0 (probe R953). If it is the "
                             "only statement, remove the ';' (then it goes to out1, probe R952), or write out1 = ...;",
                             key=("noeffect", n.line), sev="warn")
                else:
                    self.add("G122", n.line, "the value of this expression is not used (it is not sent to out1). Only a "
                             "codebox that is a single expression without ';' sends it to out1 (probes R952, R953). "
                             "Assign it, e.g. out1 = ...;", key=("noeffect", n.line))
        elif k == "if":
            self.expr(n.cond)
            self.sub(n.then, n.then_braced)
            if n.els is not None:
                self.sub(n.els, n.els_braced)
        elif k == "for":
            for s in n.init:                 # loop variable lives in the enclosing scope (gen.maxhelp: out = i)
                self.stmt(s)
            if self.in_func is None:
                self.cur_node = n            # the condition's record (MainFlow.st_of) is the for statement's
            self.push()
            self.block_depth += 1
            self.loop_depth += 1
            if n.cond:
                self.expr(n.cond)
            self.block_order(n.body)
            for s in n.body:
                self.stmt(s)
            for s in n.step:
                self.stmt(s)
            self.loop_depth -= 1
            self.block_depth -= 1
            self.pop()
        elif k == "while":
            self.expr(n.cond)
            self.loop_depth += 1
            self.sub(n.body, n.braced)
            self.loop_depth -= 1
        elif k == "block":
            self.sub(n.body, plain=True)

    def inlet_assign(self, n, name, line):
        """G120: in1 = ... fails in the C compiler at audio start (probe R228, in1 read afterwards). Bare in is in1
        (probe R954). in0 is a plain variable (inlets start at in1, probe R1235). A statement whose value is never
        used is dropped before names are checked, also for an inlet (probe R1225)"""
        core = ("'%s' is an inlet and cannot be assigned. Max: C compile error \"cannot assign to variable 'in1' with "
                "const-qualified type\" when audio starts (probe R228, measured for in1%s)"
                % (name, "; bare in is in1, probe R954" if name == "in" else ""))
        fix = "Copy it to a variable first: x = %s;" % name
        if re.fullmatch(r"in0\d*", name):
            self.add("G120", line, "'%s' looks like an inlet, but inlets start at in1: Max 9.1.4 and 9.2.0 treat it as "
                     "a plain variable (probe R1235: in0 = 3 then reads 3). A clearer name avoids the confusion" % name,
                     key=("in", name), sev="info")
        elif self.dead_stmt(n):
            self.add("G120", line, sentences(core, "Not an error here: this value is never used, and Max 9.1.4 and "
                                                   "9.2.0 drop the statement before they check names (probe R1225)",
                                             fix), key=("in", name), sev="warn")
        elif self.flow is not None and self.flow.st_of.get(id(n)) is not None and \
                max(self.flow.st_of[id(n)].level, self.flow.st_of[id(n)].nlevel) < 2:
            st = self.flow.st_of[id(n)]
            self.add("G120", line, sentences(core, self.level_note(1, st.why or st.nwhy), fix), key=("in", name),
                     sev="warn")
        else:
            self.add("G120", line, sentences(core, fix), key=("in", name))

    def multi_assign(self, n):
        """G127: 'a, b = in1 + 3' gives b = 0 (probe R642). Only the last value spreads, and only a call can have
        several outputs (probes R957, R958), so a last value that is not a call fills one name"""
        if len(n.targets) < 2:
            return
        parts = split_commas(n.expr.toks)
        last = parts[-1]
        if len(parts) >= len(n.targets) or not last:
            return
        if len(last) >= 3 and last[0].kind == "id" and (
                (last[1].text == "(" and match_close(last, 1) == len(last) - 1) or
                (len(last) >= 5 and last[1].text == "." and last[2].kind == "id" and last[3].text == "("
                 and match_close(last, 3) == len(last) - 1)):
            return                            # f(...) may return several values
        if num_value(Expr(last)) == 0:
            return                            # 'a, b = 0;' sets every name to 0, as meant
        rest = [t for t, _ in n.targets[len(parts):]]
        self.add("G127", n.line, "%d names but %d value%s: %s get%s 0 (probe R642). Only a call with several outputs "
                 "(peek, cartopol, a function that returns a, b) fills more than one name"
                 % (len(n.targets), len(parts), "" if len(parts) == 1 else "s", ", ".join(rest),
                    "s" if len(rest) == 1 else ""), key=("fewer", n.line))

    def dead_stmt(self, n):
        """True if main-code statement n is one whose value is never used (Max drops such statements before it
        checks names: probes R220, R221, R304)"""
        if self.in_func is not None or self.flow is None or n is None:
            return False
        st = self.flow.st_of.get(id(n))
        return st is not None and not st.level and not st.nlevel

    def used_sev(self):
        """(severity, note) for a check that Max was measured to refuse only in a statement whose value is used (x.x:
        R1014, boundmode = wrap: R1102, dl(10): R1207, d.dim: R350). Max drops a main-code statement whose value is
        never used before it checks names (R1107, R1108, R1225, R1226, R1228); for these forms that was not measured,
        so such a statement only warns. Code in a function is checked when the function is called (R308)"""
        n = getattr(self, "cur_node", None)
        st = None
        if self.in_func is None and self.flow is not None and n is not None:
            st = self.flow.st_of.get(id(n))
        if st is None:
            return "error", ""
        if not st.level and not st.nlevel:
            return "warn", ("Only a warn: this value is never used, and Max 9.1.4 and 9.2.0 drop such a statement before "
                            "they check names (probes R1107, R1108, R1225, R1226, R1228); for this form that was not "
                            "measured")
        if max(st.level, st.nlevel) < 2:
            return "warn", self.level_note(1, st.why or st.nwhy)
        return "error", ""

    def silent_box(self):
        """True if the codebox assigns no output (out1, out, ...) and has no History, Delay, poke or other write: then
        nothing it computes leaves it"""
        if getattr(self, "_silent", None) is None:
            hist = {k for k, v in self.decls.items() if v[0] in ("History", "Delay")}
            silent = True
            for x, _ in walk_nodes(self.items):
                if x.kind == "decl" and x.kw in ("History", "Delay"):
                    hist |= {it[0] for it in x.items}
            for x, _ in walk_nodes(self.items):
                if x.kind == "assign" and any(OUT_NAME.match(t) or t == "out" or t in hist for t, _ in x.targets):
                    silent = False
                for e in node_exprs(x):
                    for c in e.all_calls():
                        if c.name in ("poke", "splat", "write") or c.name in self.abstractions or (
                                self.ref and c.obj is None and c.name not in self.funcs and not self.ref.callable(c.name)):
                            silent = False
            self._silent = silent
        return self._silent

    def no_effect(self, e):
        """an expression with no calls, or only calls to Gen operators that have no side effect"""
        for c in e.all_calls():
            if (c.obj is not None or c.name in self.funcs or c.name in self.abstractions or c.name in ("poke", "splat")
                    or not (self.ref and c.name in self.ref.ops)):
                return False
        return True

    def sub(self, body, braced=True, plain=False):
        """every if/else/while body opens a scope, with or without braces (round 6: P-14, P-23 fail)"""
        self.push()
        self.block_depth += 1
        self.block_order(body)
        for s in body:
            self.stmt(s)
        self.block_depth -= 1
        self.pop(plain)

    def check_exprs(self, n):
        for e in node_exprs(n):
            self.expr(e, values=False)        # declaration arguments: a Buffer name is a string

    # ---- reads
    def read(self, name, line, key=None):
        """a read of name at line. key identifies the read for the main-code flow analysis (MainFlow.uses)"""
        if self.visible(name) or name in self.decls:
            return
        if name in self.patcher_params:
            if self.in_func is not None:
                self.add("G205", line, "%s() reads '%s', a param of the gen patcher, which a function cannot see (it "
                         "works in the main code: probes R240, R636). Max 9.1.4 and 9.2.0 refuse it when audio starts "
                         "(probe R1042). Pass it in as an argument" % (self.in_func.name, name),
                         key=(self.in_func.name, name))
            return                            # read bare in the main code, also with an operator name (R240, R241)
        if self.in_func is not None and re.fullmatch(r"in\d*", name):
            fn = self.in_func.name
            if name == "in":
                self.add("G205", line, "%s() reads 'in' (= in1 in the main code, probe R954), which a function cannot "
                         "see. Max 9.1.4 and 9.2.0 refuse it when audio starts (probe R1052; in1 there: \"use of "
                         "undeclared identifier 'in1'\", probe R210). Pass it in as an argument" % fn, key=(fn, name))
            else:
                self.add("G205", line, "%s() reads the inlet %s, which a function cannot see. Max: C compile error "
                         "\"use of undeclared identifier '%s'\" when audio starts (probe R210). Pass it in as an argument"
                         % (fn, name, name), key=(fn, name))
            return
        if re.fullmatch(r"(in|out)\d+", name):
            return
        if name == "mc_channel":
            self.add("G406", line, "mc_channel: inside poly~ every channel can get 1. Pass the number in with an inlet or Param", key="mc")
        if name in EXTRA_BARE:
            return
        if name in GLOBALS or self.is_constant(name) or (self.ref and self.ref.bare_ok(name)):
            return
        assigned = name in (self.top_names if self.in_func is None else self.fdefs)
        if name.isupper() and not assigned:  # VOICE assigned by the code is an ordinary variable (R171: no global VOICE)
            low = name.lower()
            if low in GLOBALS or (self.ref and low in self.ref.ops and self.ref.ops[low]["cat"] == "global"):
                self.undefined_read("G125", name, line, key,
                                    "'%s' does not exist: the Gen global is '%s' (lower case). Only constants have "
                                    "upper-case forms (PI, SAMPLERATE: probes R170, R172). Max: 'variable %s is not "
                                    "defined' when audio starts (probes R171, R335)" % (name, low, name), "Write %s" % low,
                                    dead="Not an error here: this value is never used, and Max 9.1.4 and 9.2.0 drop the "
                                         "statement (probe R1108)")
                return
            if self.is_constant(low) or (self.ref and self.ref.bare_ok(low)):
                return
        if self.in_func is not None:
            self.func_read(name, line)
            return
        if ((self.ref and self.ref.callable(name)) or name in MEASURED_BARE_FAIL) and name not in self.top_names:
            if name in MEASURED_BARE_FAIL:
                self.undefined_read("G108", name, line, key, "'%s' is a gen operator used without (). Max: 'variable %s "
                                    "is not defined' when audio starts (probe P-11), unless the gen patcher has a "
                                    "[param %s] (then say so with --param %s; probe R240)" % (name, name, name, name),
                                    "Write %s()" % name, dead="Not an error here: this value is never used, and Max "
                                    "9.1.4 and 9.2.0 drop the statement (probe R1107)")
            elif self.patcher_complete:
                self.undefined_read("G108", name, line, key, "'%s' is a gen operator used without (), and the gen "
                                    "patcher has no [param %s] (--complete-params). Max: 'variable %s is not defined' "
                                    "when audio starts (probe P-11, measured for noise; a name with no box: probe "
                                    "R1109)" % (name, name, name), "Write %s() if you meant the operator" % name)
            else:
                # a gen patcher's [param rate] is read bare, also with an operator name (probes R240, R636): gencheck
                # cannot see the patcher, so this is not an error (like G104)
                self.undefined_read("G108", name, line, key, "'%s' is a gen operator used without (). Fine if the gen "
                                    "patcher has a [param %s] (a patcher param named like an operator is read bare: "
                                    "probes R240, R636; say so with --param %s); otherwise Max: 'variable %s is not "
                                    "defined' when audio starts (probe P-11, measured for noise)" % (name, name, name, name),
                                    "Write %s() if you meant the operator" % name, cap="warn")
            return
        if name in self.defs and self.main_var_read(name, line, key):
            return
        if name in self.funcs:
            self.undefined_read("G108", name, line, key, "'%s' is a user function used without (). Max 9.1.4 and 9.2.0 "
                                "refuse a used value like this (probe R1227)" % name, "Write %s(...)" % name,
                                dead="Not an error here: this value is never used, and Max drops the statement (probe "
                                     "R1228)")
            return
        if self.patcher_complete:
            self.undefined_read("G104", name, line, key, "'%s' is not defined in this codebox, and the gen patcher has no "
                                "param, history or data box of this name (--complete-params). Max: 'variable %s is not "
                                "defined' when audio starts (probe R1109, 9.1.4 and 9.2.0)" % (name, name),
                                "Define %s, or check the spelling. A Param of another codebox in the same gen patcher "
                                "counts as a param: pass it with --param %s" % (name, name),
                                dead="Not an error here: this value is never used, and Max drops such statements with "
                                     "their 'not defined' errors (probes R140, R221)")
            return
        uses = self.flow.by_name.get(self.flow.norm(name), []) if self.flow is not None else []
        if uses and all(self.flow.level_of(u)[0] == 0 for u in uses):
            # every read of the name is in a statement whose value is never used (R140: Max drops it and compiles)
            self.add("G104", line, "'%s' is not defined in this codebox. Its value is never used here (it reaches no "
                     "output, History, Delay or poke), so Max drops the statement and compiles (probes R140, R221). "
                     "Remove the statement, or define %s" % (name, name), key=name)
            return
        self.add("G104", line, "'%s' is not defined in this codebox. Fine only if the gen patcher has a param "
                 "of this name (Params, Data and History are shared by all codeboxes in a gen patcher, probes "
                 "R1410-R1412; say so with --param %s) or a [history %s] / [data] box (readable by name, probes "
                 "R1420, R1422); otherwise Max: "
                 "'variable %s is not defined' (probe R1109). If the patcher has no other named box, say so with "
                 "--complete-params" % (name, name, name, name), key=name)

    def func_read(self, name, line):
        """a name read inside a user function that is not its parameter or local, a constant or a global. A function
        sees only those (probes R200-R202, R210, R310-R315, R445, R446)"""
        fn = self.in_func.name
        key = (fn, name)
        if name in self.dead:
            self.add("G102", line, "'%s' is first assigned inside a block (line %d) of %s() and read outside it. Inside a "
                     "function every block variable is local, also after an if without else and for a constant. Max: "
                     "'variable %s is not defined' (probes R131, R211, R605). Assign it before the block, e.g. "
                     "%s = 0;" % (name, self.dead[name], fn, name, name), key=key)
            return
        later = [x for x in self.fdefs.get(name, []) if x >= line]
        if later:
            self.add("G103", line, "'%s' is read here but first assigned at line %d of %s(). Max: 'variable %s is not "
                     "defined' (probe R203). Move the line below" % (name, min(later), fn, name), key=key)
            return
        kind = self.main_decls.get(name, (None,))[0]
        if kind:
            probe = {"History": "R201", "Param": "R202", "Data": "R314", "Buffer": "R1043", "Delay": "R1044"}.get(kind)
            if probe:
                fix = ("pass the %s as an argument: %s(%s, ...) (probe R313)" % (kind, fn, name)
                       if kind in ("Data", "Buffer") else "pass its value in as an argument")
                said = ("Max: 'variable %s is not defined' when audio starts (probe %s)" % (name, probe)
                        if kind in ("History", "Param", "Data") else "Max 9.1.4 and 9.2.0 refuse it (probe %s)" % probe)
                self.add("G205", line, "%s() uses the %s '%s' of the main code, which a function cannot see. %s. "
                         "Instead %s" % (fn, kind, name, said, fix), key=key)
            else:
                self.add("G205", line, "%s() uses the %s '%s' of the main code. Not measured for a %s, but a function "
                         "cannot see the main code's History, Param or Data (probes R201, R202, R314). Pass it as an "
                         "argument" % (fn, kind, name, kind), key=key, sev="warn")
            return
        if name in self.top_names:
            self.add("G205", line, "%s() reads '%s', a variable of the main code, which a function cannot see. Max: "
                     "'variable %s is not defined' when audio starts (probe R200). Pass it in as an argument"
                     % (fn, name, name), key=key)
            return
        if (self.ref and self.ref.callable(name)) or name in MEASURED_BARE_FAIL:
            if name in MEASURED_BARE_FAIL:
                self.add("G108", line, "'%s' is a gen operator used without (). Max: 'variable %s is not defined' "
                         "when audio starts (probe P-11). Write %s()" % (name, name, name), key=name)
            else:
                self.add("G108", line, "'%s' is a gen operator used without () in %s(). Max: 'variable %s is not "
                         "defined' (probe P-11, measured for noise). A param of the gen patcher with this name does not "
                         "help: a function cannot see patcher params (probe R1042). Write %s() if you meant the operator, "
                         "or pass the value in as an argument" % (name, fn, name, name), key=name)
            return
        if name in self.funcs:
            self.add("G108", line, "'%s' is a user function used without () in %s(). Max 9.1.4 and 9.2.0 refuse a used "
                     "value like this (probe R1227; in a statement whose value is never used it runs, probe R1228). Write "
                     "%s(...)" % (name, fn, name), key=name)
            return
        self.add("G205", line, "%s() reads '%s', which is not defined in the function. Max: 'variable %s is not defined' "
                 "once the function is called, even when its result is not used (probe R308). A function sees only its "
                 "arguments and locals, not even the gen patcher's params (probe R1042). Pass values in as arguments"
                 % (fn, name, name), key=key)

    # ---- main code: reads that no earlier assignment at this block level (or an enclosing one) defines
    def undefined_read(self, rule, name, line, key, core, fix, cap="error", dead=None):
        """G108 / G125: Max reports the name as 'variable X is not defined'. In the main code Max drops a statement
        whose value is never used, with its 'not defined' errors (probes R140, R221): an error only when the value is
        used (the measured cases P-11, R171, R335 were all used)"""
        u = None
        if self.in_func is None and self.flow is not None and key is not None:
            u = self.flow.uses.get(key)
        if u is None:
            self.add(rule, line, sentences(core, fix), key=name, sev=cap)
            return
        lv, why = self.flow.level_of(u)
        if lv == 2:
            self.pend(rule, name, line, cap, sentences(core, fix))
        elif lv == 1:
            self.pend(rule, name, line, "warn", sentences(core, self.level_note(lv, why), fix))
        else:
            self.pend(rule, name, line, "warn", sentences(
                core, dead or "Not an error here: this value is never used (it reaches no output, History, Delay or "
                "poke), and Max drops such statements with their 'not defined' errors (probes R140, R221); for this "
                "name that was not measured", fix))

    def pend(self, rule, name, line, sev, msg):
        """keep the most severe G102 / G103 / G126 finding per name (a dead read first, a live one later)"""
        old = self.pending.get((rule, name))
        if old is None or SEV_RANK[sev] > SEV_RANK[old[1]]:
            self.pending[(rule, name)] = (line, sev, msg)

    def flush_pending(self):
        for (rule, name), (line, sev, msg) in sorted(self.pending.items(), key=lambda kv: kv[1][0]):
            self.add(rule, line, msg, key=("main", name), sev=sev)
        self.pending = {}

    @staticmethod
    def level_note(lv, why):
        if lv == 1:
            return ("Not an error here: the value only reaches %s, which was not measured (Max may drop the "
                    "statement)" % (why or "a call"))
        return ""

    def main_var_read(self, name, line, key):
        """G102 / G103 / G126 for a main-code read of a variable that is assigned somewhere in the main code, but by
        no assignment before this read at the same or an enclosing block level. Returns False if not handled"""
        u = self.flow.uses.get(key) if self.flow is not None and key is not None else None
        if u is None:                         # a declaration argument, or the flow analysis failed
            if name in self.dead:
                self.pend("G102", name, line, "warn", "'%s' is first assigned inside a block (line %d) and read outside "
                          "it. Not analysed here; Max refuses this unless the value is a constant (probes R800, R600)"
                          % (name, self.dead[name]))
                return True
            later = [d[0] for d in self.defs.get(name, []) if d[0] >= line]
            if later:
                self.pend("G103", name, line, "warn", "'%s' is read here but first assigned at line %d. Not analysed "
                          "here; Max refuses a used value read before its assignment (probe P01)" % (name, min(later)))
                return True
            return False
        if u.visible:
            return True                       # the two scope walks disagree (a gencheck bug): no finding
        if u.leak:
            self.block_var_read(u, name, line)
        else:
            self.read_before_def(u, name, line)
        return True

    def read_before_def(self, u, name, line):
        """G103: no assignment of name before this read (it is assigned at this statement or later)"""
        f = self.flow
        lv, why = f.level_of(u)
        first = f.first_def(name, u.st.idx) or line
        inblock = u.st.block is not f.top
        if name in u.st.targets:              # x -= 1, x = x + 1
            what = "'%s'" % short(f.stmt_text(u.st, name), 50)
            if lv == 0:
                self.pend("G103", name, line, "info", sentences(
                    "%s reads %s before any assignment, but the result is never used (it is overwritten first, or "
                    "reaches no output, History, Delay or poke), so Max drops it (probes R301, R430)" % (what, name),
                    "If you meant to use it, assign %s first" % name))
                return
            later = f.later_live_use(name, u.st.idx)
            msg = ["%s%s reads %s, which is not assigned before it%s. Max: 'variable %s is not defined' when audio "
                   "starts (probes %s)" % (what, " inside the block" if inblock else "", name,
                                           ", and %s is used later (line %d)" % (name, later.line) if later else "",
                                           name, "R303, R224, R604" if inblock else "R141, R432"),
                   self.level_note(lv, why),
                   "Assign %s before %s, e.g. %s = 0;" % (name, "the block" if inblock else "it", name)]
        elif lv == 0:
            self.pend("G103", name, line, "info", sentences(
                "'%s' is read here before it is first assigned (line %d), but this value is never used (it reaches no "
                "output, History, Delay or poke), so Max drops %s (probes %s)" % (
                    name, first, "this item of the comma list" if u.item is not None else "the statement",
                    "R1224, R221" if u.item is not None else "R221, R300, R437"),
                "It fails once the value is used"))
            return
        elif inblock:
            msg = ["'%s' is read inside the block before it is first assigned (line %d). Max: 'variable %s is not "
                   "defined' when audio starts (probe R11)" % (name, first, name), self.level_note(lv, why),
                   "Assign it before the block"]
        else:
            msg = ["'%s' is read here but first assigned at line %d. Max: 'variable %s is not defined' when audio "
                   "starts (probes P01, R10, R434)" % (name, first, name), self.level_note(lv, why),
                   "Move the line below, or use a History for the previous value"]
        if u.st.multi:
            msg.insert(-1, MULTI_NOTE)
        self.pend("G103", name, line, "error" if lv == 2 and not u.st.multi else "warn", sentences(*msg))

    def copies_outer(self, d, read):
        """d is 't = src' inside a block, t is read after it by read: does src have a value from before the blocks
        that t leaks out of (an assignment at the level of the read, or an enclosing one, reaches 't = src')? Only
        that form was measured on 9.1.x (k = 4 before the block: R1071; i = 0 before the loop: R1080). A src
        assigned only inside those blocks holds a value computed there (R404, R412, R801)"""
        u = self.flow.uses.get((id(d.rhs), 0))
        if u is None or not u.visible:
            return False
        outer, b = set(), read.st.block
        while b is not None:
            outer.add(id(b))
            b = b.parent
        return any(id(x.block) in outer for x in u.rd)

    def block_var_read_914(self, u, name, line, defs, where, fix, plain, lv, why):
        """G102 / G126 judged as Max 9.1.x (results914_11-16): a constant OR a plain copy of in1, elapsed, a Param or
        another variable that has a value before the block (R1071, R1080) leaks out of the block; a computed value, a
        History, samplerate, or constants in both if/else branches fail"""
        f = self.flow
        kinds, alias = [], None
        for d in defs:
            c = f.leak_class(d)
            toks = d.rhs.toks if d.rhs is not None else []
            src = toks[0].text if len(toks) == 1 and toks[0].kind == "id" else None
            if d.selfref:
                k = "const" if all(f.leak_class(e) == CONST for e in defs if not e.selfref) else "unknown"
            elif c == CONST:
                k = "const"
            elif d.op == "=" and src is not None and (
                    IN_NAME.match(src) or src == "elapsed" or f.decl_kind.get(src) == "Param" or
                    (src in f.def_list and src not in f.decl_kind and self.copies_outer(d, u))):
                k, alias = "alias", src
            elif c == NONCONST:
                k = "other"
            else:
                k = "unknown"
            kinds.append(k)
        ks = set(kinds)
        if lv == 0:
            return                            # never used: Max drops it on 9.1.4 too (probes R220, R422)
        ver = self.max_version_text
        sev = "error" if lv == 2 and not plain and not u.st.multi else "warn"
        if (u.both and ks == {"const"}) or "other" in ks:
            if u.both:
                core = ("'%s' is assigned in both branches of the if/else at line %d, not before it, and read after it "
                        "here. Max %s: 'variable %s is not defined' when audio starts (probes R401, R904, R03, R05 on "
                        "9.1.4)" % (name, min(u.both), ver, name))
                fix = "Assign %s before the if, e.g. %s = 0;" % (name, name)
            else:
                bad = defs[kinds.index("other")]
                core = ("'%s' is first assigned inside %s, not before it, and read after the block here. The value "
                        "assigned there (%s) is computed, a History or samplerate. Max %s: 'variable %s is not defined' "
                        "when audio starts (probes R404, R412, R801, R804, R902 on 9.1.4)"
                        % (name, where, short(pretty(bad.rhs)), ver, name))
            self.pend("G102", name, line, sev, sentences(core, plain, MULTI_NOTE if u.st.multi else "",
                                                         self.level_note(lv, why), fix))
            return
        if ks <= {"const", "alias"} and (not u.both or "const" in ks):
            if "const" in ks:
                last = [d for d, k in zip(defs, kinds) if k == "const"][-1]
                v = f.const_value(last)
                value = short(pretty(last.rhs)) if v is None or last.rhs is None else "%g" % v
                if "alias" in ks:
                    value += " (the constant wins over the plain copy of %s, probes R907, R908, R916)" % alias
            elif alias in f.def_list and alias not in f.decl_kind:
                self.pend("G126", name, line, "warn", sentences(
                    "'%s' is assigned only inside %s, never before it, as a plain copy of the variable %s. Max %s "
                    "compiles this, but after the block %s does not follow the block: on 9.1.4 the same form gave the "
                    "value %s had before the block (probe R1071) or 0 (probe R1080), whether the block ran or not. "
                    "Max 9.2.0 refuses it" % (name, where, alias, ver, name, alias), plain,
                    self.level_note(lv, why), fix))
                return
            elif IN_NAME.match(alias):
                self.pend("G126", name, line, "warn", sentences(
                    "'%s' is assigned only inside %s, never before it, as a plain copy of %s. Max 9.1.5 compiles "
                    "this (probes R1548-R1550: if, for and while; 9.1.4 was not measured for this form); what %s "
                    "holds after the block was not measured. For elapsed and a Param in the same place it always "
                    "held that value, even when the block did not run (probes R800, R903 on 9.1.4). Max 9.2.0 "
                    "refuses it (R1548-R1550)" % (name, where, alias, name), plain, self.level_note(lv, why), fix))
                return
            else:
                value = "the value of %s" % alias
            self.pend("G126", name, line, "warn", sentences(
                "'%s' is assigned only inside %s, never before it. Max %s compiles this, but after the block %s "
                "always holds %s, even when that code does not run (probes R600, R800, R807, R808, R903 on 9.1.4). "
                "Max 9.2.0 refuses some of these forms" % (name, where, ver, name, value), plain,
                self.level_note(lv, why), fix))
            return
        self.pend("G102", name, line, "warn", sentences(
            "'%s' is first assigned inside %s, never before it, and read after the block here. This combination was "
            "not measured on Max %s: it may leak a value out of the block or fail with 'variable %s is not defined'"
            % (name, where, ver, name), plain, self.level_note(lv, why), fix))

    def block_reads(self, d):
        """names read by assignment d that get a constant value inside a block, which Max 9.2.0 never treats as a
        compile-time constant (probes R1070, R1071), in reading order. Empty if any read is not constant for another
        reason (an inlet, Param, History, elapsed, samplerate, a value computed or counted in a loop: their own
        probes)"""
        f = self.flow
        if d.rhs is None or d.op != "=":
            return []
        out = []
        for k in range(len(d.rhs.all_reads())):
            u = f.uses.get((id(d.rhs), k))
            if u is None:
                return []
            inner = [x for x in u.rd if x.block is not f.top]
            if inner:
                if any((x.selfref and x.block.loop) or f.const_def(x, set()) != CONST for x in inner):
                    return []
                if u.name not in out:
                    out.append(u.name)
            elif f.const_use(u, set()) != CONST:
                return []
        return out

    def block_var_read(self, u, name, line):
        """G102 / G126: name is assigned before this read only inside blocks that are closed here (rounds 11-14)"""
        f = self.flow
        lv, why = f.level_of(u)
        defs = sorted(set(u.leak), key=lambda d: d.st.idx)
        anc, b = set(), u.st.block
        while b is not None:
            anc.add(id(b))
            b = b.parent
        kinds, blocks = set(), []
        for d in defs:
            if d.block not in blocks:
                blocks.append(d.block)
            b = d.block
            while b is not None and id(b) not in anc:
                kinds.add(b.kind)
                b = b.parent
        cls, bad = CONST, None
        for d in defs:
            c = f.leak_class(d)
            if c > cls:
                cls, bad = c, d
        if bad is not None and bad.op != "=" and any(cu.compound and not cu.visible and not cu.leak
                                                    for cu in bad.st.uses if cu.name == name):
            return                            # 'x -= 1' on a never-assigned x: G103 reports it there
        first = defs[0]
        if len(blocks) > 1:
            where = "blocks at lines %s" % ", ".join(str(b.line) for b in blocks[:4])
        else:
            where = "%s at line %d" % (BLOCK_WORDS.get(first.block.kind, "a block"), first.line)
        fix = "Assign %s before the block, e.g. %s = 0;" % (name, name)
        plain = "Not measured for a { } block without if/for/while" if "plain" in kinds else ""
        selfref = name in u.st.targets
        top = u.st.block is f.top
        if self.old_max():
            self.block_var_read_914(u, name, line, defs, where, fix, plain, lv, why)
            return
        if u.both or cls == NONCONST or selfref:
            if u.both:
                where = "both branches of the if/else at line %d" % min(u.both)
                core = ("'%s' is assigned in %s, not before it, and read after it here. Max: 'variable %s is not "
                        "defined' when audio starts, even when both branches assign the same constant (probes R401, "
                        "R403, R904)" % (name, where, name))
                fix = "Assign %s before the if, e.g. %s = 0;" % (name, name)
            elif cls == NONCONST:
                if bad.selfref:
                    core = ("'%s' is first assigned inside %s, not before it, and read after the block here. There "
                            "'%s' updates it from its own value, which is not a compile-time constant. Max: 'variable "
                            "%s is not defined' when audio starts, or an internal name such as 'tmp_t_486' (probe "
                            "R807)" % (name, where, short(f.stmt_text(bad.st, name)), name))
                else:
                    inner = self.block_reads(bad)
                    probes = ("probe R404" if "while" in kinds else "probes P24, R412, R606" if "for" in kinds else
                              "probes R800, R903, R907")
                    if inner:
                        # 9.2.0: a value assigned inside a block is never a compile-time constant (probes R1070, R1071)
                        core = ("'%s' is first assigned inside %s, not before it, and read after the block here. The "
                                "value assigned there (%s) reads %s, which gets a value inside a block; Max 9.2.0 never "
                                "treats such a value as a compile-time constant, even a constant one (a = 5; t = a * 2 "
                                "in the block: probe R1070; k = 4 before and k = 5 in a block: probe R1071), so: "
                                "'variable %s is not defined' when audio starts (Max 9.1.4 runs those two)"
                                % (name, where, short(pretty(bad.rhs)), " and ".join(inner[:2]), name))
                    else:
                        core = ("'%s' is first assigned inside %s, not before it, and read after the block here. The "
                                "value assigned there (%s) is not a compile-time constant, so Max: 'variable %s is not "
                                "defined' when audio starts (%s)" % (name, where, short(pretty(bad.rhs)), name, probes))
            else:
                core = ("'%s' at line %d reads %s, which so far is assigned only inside %s, never before it. Max 9.2.0 "
                        "refuses it when audio starts (probe %s; Max 9.1.4 runs it and %s keeps the leaked value)"
                        % (short(f.stmt_text(u.st, name)), line, name, where, "R808" if top else "R1061, R808 at the "
                           "top level", name))
            if lv == 0:
                self.pend("G102", name, line, "info", sentences(
                    "'%s' is assigned in %s, not before it, and read after the block here, but this value is never used "
                    "(it reaches no output, History, Delay or poke), so Max drops the statement and compiles (probes "
                    "R220, R422)" % (name, where), "It fails once the value is used", fix))
                return
            sev = "error" if lv == 2 and not plain and not u.st.multi else "warn"
            self.pend("G102", name, line, sev, sentences(core, plain, MULTI_NOTE if u.st.multi else "",
                                                         self.level_note(lv, why), fix))
            return
        if lv == 0:
            return                            # a constant that leaks into a dropped statement: harmless
        if cls == UNKNOWN:
            odd = next(d for d in defs if f.leak_class(d) == UNKNOWN)
            text = f.stmt_text(odd.st, name) if odd.selfref else pretty(odd.rhs)
            self.pend("G102", name, line, "warn", sentences(
                "'%s' is first assigned inside %s, never before it, and read after the block here. Not measured for "
                "this value (%s): if Max treats it as a compile-time constant, %s always holds it, even when the block "
                "does not run (probes R600, R925); if not, Max refuses the code: 'variable %s is not defined' (probes "
                "R800, R903)" % (name, where, short(text), name, name), plain, self.level_note(lv, why), fix))
            return
        last = defs[-1]
        v = f.const_value(last)
        text = short(pretty(last.rhs))
        value = text if v is None else "%g" % v if num_value(last.rhs) is not None else "%s (= %g)" % (text, v)
        if last.zero:
            value = "0 (a name with no value of its own in 'a, b = x' gets 0, probe R642)"
        if len(defs) > 1:
            value += ", the last constant assigned to it (line %d)" % last.line
        loops = kinds & {"for", "while"}
        when = ("the loop body does not run" if loops and not kinds & {"if", "else"} else
                "the condition is false" if not loops else "that code does not run")
        probes = ["R600", "R812"] if kinds & {"if", "else"} else []
        probes += ["R905"] if "for" in kinds else []
        probes += ["R1062"] if "while" in kinds else []
        probes += ["R803"] if len(defs) > 1 else []
        note = ""
        self.pend("G126", name, line, "warn", sentences(
            "'%s' is assigned only inside %s, never before it. Max compiles this, but after the block %s always holds "
            "%s, even when %s (probe%s %s)" % (name, where, name, value, when, "s" if len(probes) > 1 else "",
                                               ", ".join(probes)), note, plain, self.level_note(lv, why), fix))

    # ---- expressions
    def unary_plus(self, e):
        """G134: Max refuses a '+' that is not a binary operator, and a plus sign in an exponent: probes R1500-R1505 and
        R1507, R1510, R1511 fail on Max 9.1.4 and 9.2.0 (round 21); unary minus (R1506), 1e-3 (R1508) and 1e3 (R1509)
        work. Found through two real FDN codeboxes with '(+ a - b ...)' in the plugin eval of 2026-10-10"""
        prev = None
        for i, t in enumerate(e.toks):
            if t.text == "+" and (prev is None or (prev.kind == "op" and prev.text not in (")", "]"))):
                self.add("G134", t.line, "unary plus '+%s': Max refuses it and the gen~ is silent (probes R1500-R1505, "
                         "Max 9.1.4 and 9.2.0). Unary minus is fine (R1506). Remove the '+'"
                         % (e.toks[i + 1].text if i + 1 < len(e.toks) else ""), key=("uplus", t.line))
            elif t.kind == "num" and re.search(r"[eE]\+", t.text):
                self.add("G134", t.line, "'%s': Max refuses a plus sign in an exponent and the gen~ is silent (probes "
                         "R1507, R1510, R1511, Max 9.1.4 and 9.2.0; 1e-3 and 1e3 work, R1508, R1509). Write %s"
                         % (t.text, re.sub(r"([eE])\+", r"\1", t.text)), key=("eplus", t.line))
            prev = t

    def expr(self, e, values=True):
        self.unary_plus(e)
        if values:
            self.string_values(e)
        bufrefs = set()
        for c in e.all_calls():
            if c.obj is None and c.name in BUFFER_FUNCS and c.args and len(c.args[0].toks) == 1 \
                    and c.args[0].toks[0].kind == "id":
                bufrefs.add((c.args[0].toks[0].text, c.args[0].toks[0].line))
        words = {}                           # boundmode = wrap: a bare attribute word, not a read (G413)
        for c in e.all_calls():
            op = self.attr_owner(c)
            for k, v in c.named.items():
                if op and self.attr_word(op, k, v) == "word":
                    key = (v.toks[0].text, v.toks[0].line)
                    words[key] = words.get(key, 0) + 1
        for k, (name, line) in enumerate(e.all_reads()):
            if words.get((name, line)):
                words[(name, line)] -= 1
                continue
            if (name, line) in bufrefs and not (self.visible(name) or name in self.decls):
                if self.in_func is None and self.patcher_complete and name not in self.patcher_params:
                    self.undefined_read("G110", name, line, (id(e), k), "'%s' is not declared here, and the gen patcher "
                                        "has no data or buffer object of this name (--complete-params). Max: 'variable "
                                        "%s is not defined' (probes R1055, R1109: a name with no box fails)"
                                        % (name, name), "Add Buffer %s(\"name\") or Data %s(size)" % (name, name))
                    continue
                if self.in_func is None:
                    self.add("G110", line, "'%s' is not declared here: it must be a data or buffer object in the gen "
                             "patcher (or add Buffer %s(\"name\") / Data %s(size))" % (name, name, name), key=("buf", name))
                    continue
                if name not in self.main_decls and name not in self.top_names:
                    # a function cannot use a buffer it was not given, with or without a [data] box of that name in
                    # the gen patcher (probes R1055, R1421)
                    self.add("G110", line, sentences(
                        "%s() uses '%s', which is not declared in the function. Max 9.1.4 and 9.2.0 refuse this, also "
                        "when the gen patcher has a data or buffer object of that name: 'variable %s is not defined' "
                        "(probes R1055, R1421). A function cannot see the codebox's Data, Buffer or Delay either "
                        "(probes R314, R1043, R1044)" % (self.in_func.name, name, name),
                        "Pass it as an argument (probe R313)"),
                        key=("buf", self.in_func.name, name), sev="error")
                    continue
            self.read(name, line, (id(e), k))
        for obj, mem, line in e.all_members():
            kind = self.decls.get(obj, (None,))[0]
            sev, note = "error", ""             # also when the value is never used (probes R1440, R1443)
            if kind in ("Data", "Buffer", "Delay"):
                self.add("G108", line, sentences("'%s.%s' needs (). Max fails to compile a %s method used without () "
                                                 "(probe R350)" % (obj, mem, kind), note, "Write %s.%s()" % (obj, mem)),
                         key=(obj, mem), sev=sev)
            else:
                self.add("G129", line, sentences(
                    "'%s.%s': a '.' after a name without a method call is jit.gen vector syntax (swizzle); gen~ has "
                    "none. Max 9.1.4 and 9.2.0 refuse the codebox (probe R1014; d.dim on a Data fails too, probe R350)"
                    % (obj, mem), note, "gen~ values are single numbers: use the variable itself, or write "
                    "name.method(...) for a Data, Buffer or Delay"), key=(obj, mem), sev=sev)
        self.noise_pattern(e)
        self.fract_ok = set()                # fract(...) directly inside abs/wrap/fold/clamp/clip: sign already fixed
        for c in e.all_calls():
            if c.obj is None and c.name in ("abs", "wrap", "fold", "clamp", "clip") and c.args:
                a = c.args[0]
                if (len(a.calls) == 1 and a.calls[0].obj is None and a.calls[0].name == "fract" and a.calls[0].start == 0
                        and a.calls[0].end == len(a.toks) - 1):
                    self.fract_ok.add(id(a.calls[0]))
        heavy = [c.name for c in e.all_calls() if c.obj is None and c.name in HEAVY]
        if any(t.text == "?" for t in e.toks) and len(heavy) >= 2:
            self.add("G501", e.toks[0].line, "?: computes both sides every sample (%s). Use an if block to skip work" % ", ".join(sorted(set(heavy))), key=e.toks[0].line)
        for c in e.all_calls():
            self.call(c)

    def string_values(self, e):
        """G124: a string as a plain argument of a call (f("abc")). The user guide uses strings only for attribute
        values, Buffer names and require(). A string as a value outside any call fails (probe R1208, a parse error
        here); as a call argument it was not measured"""
        named = {id(t) for c in e.all_calls() for v in c.named.values() for t in v.toks}
        for t in e.toks:
            if t.kind == "str" and id(t) not in named:
                self.add("G124", t.line, "the string %s is an argument of a call. Strings were measured only as "
                         "attribute values, Buffer names and require() file names; as a value outside a call Max refuses "
                         "them (probe R1208); as a call argument it was not measured. Use a number, or name = \"value\" "
                         "for an attribute" % short(t.text, 30), key=("strval", t.line))
                return

    def call(self, c):
        if c.obj is not None:
            kind = self.decls.get(c.obj, (None,))[0]
            if kind in KNOWN_METHODS and c.name not in KNOWN_METHODS[kind]:
                self.add("G107", c.line, "%s '%s' has no known method .%s()" % (kind, c.obj, c.name), key=(c.obj, c.name))
            if kind in KNOWN_METHODS:
                self.attr_vars(c, self.attr_owner(c))
                self.attr_names(c, self.attr_owner(c))
            if c.name in INTERP_READERS:
                self.interp_read(c, c.args[0] if c.args else None)
            if kind == "Delay" and c.name == "read" and c.args:
                self.delay_read(c)
            return
        name = c.name
        if name in self.funcs and not self.op_named(name):
            self.arg_count(c, self.funcs[name])
            # a named argument sets a parameter (probes R180, R629) or a Param declared in the function (probe R959)
            params = set()
            for d in self.func_defs.get(name, [self.funcs[name]]):
                params |= set(d.params)
                params |= {it[0] for x, _ in walk_nodes(d.body, True) if x.kind == "decl" and x.kw == "Param"
                           for it in x.items}
            for k in sorted(c.named):
                if k not in params:
                    self.add("G416", c.line, "%s(..., %s = ...): %s() has no parameter or Param '%s' (%s). A named "
                             "argument sets the parameter or the function's Param of that name (probes R180, R629, "
                             "R959); an unknown name was not measured. Check the spelling"
                             % (name, k, name, k, ", ".join(sorted(params)) or "none"), key=("attrname", c.line, k))
            if self.in_func is not None:
                if name != self.in_func.name:
                    self.add("G204", c.line, "%s() calls the user function %s()" % (self.in_func.name, name), key=(self.in_func.name, name))
            else:
                inner = [x.name for a in c.args + list(c.named.values()) for x in a.all_calls()
                         if x.obj is None and x.name in self.funcs]
                if inner:
                    self.add("G201", c.line, "user function %s() gets another user function call (%s) in its arguments. "
                             "Runs in Max 9.2.0 (probe P-03, audio on)" % (name, ", ".join(sorted(set(inner)))), key=c.line)
                if self.block_depth > 0:
                    self.add("G202", c.line, "user function %s() is called inside a block. Runs in Max 9.2.0 (probes P-04, P-05, audio on)" % name, key=c.line)
            return
        if name == "require":
            self.add("G118", c.line, "require() works only as a line of its own at the top of the codebox, before "
                     "functions, declarations and statements. Max: 'operator require not defined' (probe R226)", key=c.line)
            return
        if name in self.decls:
            kind = self.decls[name][0]
            # a Param named like an operator is called as the operator (Param cycle(...); cycle(f) is the oscillator)
            if not (self.ref and self.ref.callable(name)) and name not in MEASURED_OP_FUNCS:
                fix = {"Delay": "%s.read(t)" % name, "Data": "peek(%s, i)" % name, "Buffer": "peek(%s, i)" % name
                       }.get(kind, name)
                if kind == "Delay":
                    sev, note = "error", ""     # also when the value is never used (probe R1442)
                    self.add("G105", c.line, sentences("'%s' is a Delay, not a function. Max 9.1.4 and 9.2.0 refuse "
                                                       "%s(...), also where the value is never used (probes R1207, "
                                                       "R1442)" % (name, name), note, "Write %s" % fix),
                             key=("declcall", name), sev=sev)
                else:
                    self.add("G105", c.line, "'%s' is a %s, not a function: %s(...) was not measured for a %s (a Delay "
                             "called this way fails, probe R1207). Write %s" % (name, kind, name, kind, fix),
                             key=("declcall", name))
            return
        if name in NOT_CALLABLE:
            if name in TESTED_NOT_CALLABLE and self.dead_stmt(getattr(self, "cur_node", None)):
                self.add("G109", c.line, "%s() is not a GenExpr function: \"use of undeclared identifier '%s'\" when audio "
                         "starts (probe P-12). Not an error here: this value is never used, and Max 9.1.4 and 9.2.0 "
                         "drop the statement (probe R1226). Use a %s declaration"
                         % (name, name, NOT_CALLABLE[name]), key=name, sev="warn")
            elif name in TESTED_NOT_CALLABLE:
                self.add("G109", c.line, "%s() is not a GenExpr function: \"use of undeclared identifier '%s'\" when audio "
                         "starts (probe P-12). Use a %s declaration" % (name, name, NOT_CALLABLE[name]), key=name)
            elif name == "delay":
                self.add("G109", c.line, "delay() is not a GenExpr function. For the declaration 'delay dl(10);' Max "
                         "says \"The delay() operator is not supported in GenExpr; use the Delay.read and Delay.write "
                         "instead.\" (probe R982); the call form itself was not measured. Write Delay dl(N); "
                         "dl.write(x); y = dl.read(t);", key=name, sev="warn")
            else:
                self.add("G109", c.line, "%s() is a graphical gen object; as a function call it was not tested. "
                         "Usually written as a %s declaration" % (name, NOT_CALLABLE[name]), key=name, sev="warn")
            return
        if self.ref and not self.ref.callable(name):
            if name in self.abstractions:
                return
            if getattr(self, "missing_libs", None):
                self.add("G105", c.line, "%s() is not known here; probably from a require()'d library that was not found "
                         "or could not be read (G117, G123)" % name, key=name, sev="info")
                return
            self.add("G105", c.line, "%s() is not a Gen operator or a user function in this codebox. Fine only if it is a gen "
                     "abstraction (%s.gendsp in the search path) or comes from require()" % (name, name), key=name)
            return
        if self.attr_owner(c):
            self.attr_vars(c, name)
            self.attr_names(c, name)
        mx = self.ref.ops[name]["maxargs"] if self.ref and name in self.ref.ops else None
        if mx is not None and len(c.args) > mx:
            self.add("G106", c.line, "%s() gets %d arguments; the Gen reference lists up to %d. min(a, b, c) runs "
                     "(probe P-10, audio on) but what the extra argument does is not confirmed" % (name, len(c.args), mx), key=c.line)
        if name in INTERP_READERS:
            self.interp_read(c, c.args[1] if len(c.args) > 1 else None)
        if name == "mc_channel":
            self.add("G406", c.line, "mc_channel(): inside poly~ every channel can get 1. Pass the number in with an inlet or Param", key="mc")
        if name == "fract" and c.args and id(c) not in self.fract_ok and not self.nonneg(c.args[0]):
            if raw_trig(c.args[0]):
                self.add("G403", c.line, "fract(sin(...)) is in (-1, 1), not [0, 1): genlib fract keeps the sign (fract(-0.25) "
                         "= -0.25, probe R490). Use wrap(x, 0, 1)", key=c.line)
            else:
                self.add("G404", c.line, "fract() of a negative number is negative in genlib. Fine for values that are always positive", key=c.line)

    def nonneg(self, e):
        """True if expression e can never be negative (interval arithmetic of genflow: constants, Param min/max in the
        main code, sin/cos in -1..1, squares, pow(x, 2))"""
        try:
            node = genflow.parse(e.toks)
        except genflow.FlowError:
            return False
        key = self.in_func is None
        fl = self.range_flow.get(key)
        if fl is None:
            params = {k: v for k, v in self.decls.items() if v[0] == "Param"} if key else {}
            fl = self.range_flow[key] = genflow.Flow([], params)
        v = fl.ival(node)
        return v is not None and v[0] >= 0

    def attr_owner(self, c):
        """the built-in operator whose attributes a call's name = value arguments set, or None (user function,
        abstraction, unknown function)"""
        if c.obj is not None:
            kind = self.decls.get(c.obj, (None,))[0]
            return ("delay" if kind == "Delay" else c.name) if kind in KNOWN_METHODS else None
        if (c.name in self.funcs and not self.op_named(c.name)) or c.name in self.decls or c.name in self.abstractions:
            return None
        if self.ref:
            return c.name if self.ref.callable(c.name) else None
        return c.name if c.name in ATTR_OPS else None

    def attr_word(self, op, k, e):
        """'var' if the value of attribute k is a variable of the code, 'word' if it is a bare word that the Gen
        reference lists as a value of k (boundmode = wrap), else None"""
        if len(e.toks) != 1 or e.toks[0].kind != "id":
            return None
        v = e.toks[0].text
        fn = self.in_func
        if (self.visible(v) or v in self.decls or v in self.patcher_params or (fn is None and v in self.top_names) or
                (fn is not None and (v in fn.params or v in self.fdefs))):
            return "var"
        enum = (self.ref.ops.get(op, {}).get("attrs", {}).get(k) if self.ref else None) or []
        return "word" if v in enum else None

    def attr_vars(self, c, op):
        """G413: name = variable in a call of a built-in operator. Attributes take a fixed value; Max reads the
        variable's name as the value and prints 'bm is not a valid value for attribute boundmode' at load, and the
        gen~ still runs with the default setting (probes R960, R1103). A bare word (boundmode = wrap) fails (probe
        R1102); a misspelled quoted value runs with the default (probe R1209)"""
        for k, e in c.named.items():
            kind = self.attr_word(op, k, e)
            v = e.toks[0].text if kind else None
            enum = (self.ref.ops.get(op, {}).get("attrs", {}).get(k) if self.ref else None) or []
            if kind == "word":
                sev, note = self.used_sev()
                self.add("G413", c.line, sentences("%s(..., %s = %s): an attribute value without quotes. Max 9.1.4 and "
                                                   "9.2.0 refuse the codebox (probe R1102)" % (c.name, k, v), note,
                                                   "Write %s = \"%s\"" % (k, v)),
                         key=("attrvar", c.line, k), sev=sev)
            elif (kind is None and enum and len(e.toks) == 1 and e.toks[0].kind == "str"
                  and e.toks[0].text[1:-1] not in enum):
                v = e.toks[0].text[1:-1]
                self.add("G413", c.line, "%s(..., %s = \"%s\"): '%s' is not a value of %s (one of: %s). Max 9.1.4 and "
                         "9.2.0 run it, but the setting is ignored: %s uses its default %s (probe R1209). Check the "
                         "spelling" % (c.name, k, v, v, k, ", ".join(sorted(enum)), c.name, k),
                         key=("attrvar", c.line, k))
            elif kind == "var" and v not in enum:
                self.add("G413", c.line, "%s(..., %s = %s): '%s' is a variable, but an attribute takes a fixed value. "
                         "Max 9.2.0 prints \"%s is not a valid value for attribute %s\" at load and the gen~ runs with "
                         "the default %s: the variable's value is ignored (probes R960, R1103, also on 9.1.4). Write the "
                         "value itself%s"
                         % (c.name, k, v, v, v, k, k, ", one of: " + ", ".join(sorted(enum)) if enum else ""),
                         key=("attrvar", c.line, k))

    def attr_names(self, c, op):
        """G416: name = value in a call of a built-in operator, where name is not an attribute the Gen reference lists
        for it (sample(..., interpolation = "linear"), cos(x = in1)). Max reports an unknown Param attribute ('mn is
        not a valid attribute of Param', probe R78); for an operator Max runs and ignores it (probe R1210)"""
        if not op or not self.ref or op not in self.ref.ops:
            return
        attrs = self.ref.ops[op].get("attrs", {})
        for k in sorted(c.named):
            if k in attrs:
                continue
            if attrs:
                what = "'%s' is not an attribute of %s() (%s)" % (k, op, ", ".join(sorted(attrs)))
            else:
                what = ("'%s' is not an attribute of %s() (it lists none). In a call, 'name = value' sets an attribute; "
                        "it does not assign %s" % (k, op, k))
            self.add("G416", c.line, "%s(..., %s = ...): %s. Max 9.1.4 and 9.2.0 ran peek(..., boundmod = \"wrap\") "
                     "and ignored the setting (probe R1210). Check the spelling"
                     % (c.name, k, what), key=("attrname", c.line, k))

    def arg_count(self, c, f):
        """G208: Max gives no message for a call with too few or too many arguments"""
        defs = self.func_defs.get(c.name, [f])
        if len(defs) > 1:
            fits = [d for d in defs if len(c.args) <= len(d.params) and
                    all(p in d.defaults or p in c.named for p in d.params[len(c.args):])]
            if fits:
                return
        n, k = len(c.args), len(f.params)
        if n > k:
            self.add("G208", c.line, "%s() has %d parameter%s but gets %d arguments here. Max ignores the extra ones "
                     "without a message (probe R621)" % (c.name, k, "" if k == 1 else "s", n), key=("args+", c.line, c.name))
            return
        missing = [p for p in f.params[n:] if p not in f.defaults and p not in c.named]
        if missing:
            self.add("G208", c.line, "%s() gets %d argument%s here but has %d parameters: %s %s 0, and Max gives no "
                     "message (probe R620). If that is meant, give a default: %s(..., %s = 0) (probe R628)"
                     % (c.name, n, "" if n == 1 else "s", k, ", ".join(missing), "is" if len(missing) == 1 else "are",
                        c.name, missing[0]), key=("args-", c.line, c.name))

    def interp_read(self, c, index):
        if c.name == "peek" and "boundmode" not in c.named:
            self.add("G402", c.line, "peek without boundmode: an out-of-range index reads 0 (default 'ignore', probe "
                     "R975)", key=c.line)

    def delay_read(self, c):
        d = self.decls.get(c.obj)
        if not d or not d[2]:
            return
        size, t = num_value(d[2][0]), num_value(c.args[0])
        if size is not None and t is not None and t > size:
            self.add("G408", c.line, "%s.read(%g) is longer than Delay %s(%g); the read is clipped to the Delay length" % (c.obj, t, c.obj, size), key=c.line)

    def noise_pattern(self, e):
        s = " ".join(t.text for t in e.toks)
        if re.search(r"noise \( \) \* 2(\.0*)? - 1(\.0*)?\b", s) or re.search(r"\b2(\.0*)? \* noise \( \) - 1(\.0*)?\b", s):
            self.add("G405", e.toks[0].line, "noise() is already -1..1; noise()*2-1 gives -3..1. For 0..1 use noise()*0.5+0.5", key=e.toks[0].line)


# ----------------------------------------------------------------- driver


def strip_comments(src):
    """src without // and /* */ comments (an unclosed /* runs to the end), in linear time: a non-greedy regex for
    block comments rescans to the end of the file from every unclosed /*"""
    out, i, n = [], 0, len(src)
    while i < n:
        j = src.find("/", i)
        if j < 0 or j + 1 >= n:
            out.append(src[i:])
            break
        nxt = src[j + 1]
        if nxt == "/":
            out.append(src[i:j])
            k = src.find("\n", j)
            i = n if k < 0 else k
        elif nxt == "*":
            out.append(src[i:j])
            k = src.find("*/", j + 2)
            i = n if k < 0 else k + 2
        else:
            out.append(src[i:j + 1])
            i = j + 1
    return "".join(out)


def idents_and_decls(src):
    try:
        items = Parser(tokenize(src)).program()
    except ParseError:
        return set(re.findall(r"[^\W\d]\w*", strip_comments(src))), set()
    names, decls = set(), set()
    for n, _ in walk_nodes(items):
        if n.kind == "decl":
            decls |= {it[0] for it in n.items}
        if n.kind == "assign":
            names |= {x for x, _ in n.targets}
        for e in node_exprs(n):
            names |= {x for x, _ in e.all_reads()}
    return names | decls, decls


_LIB_INDEX = {}
_DIR_INDEX = {}


def max_app_resources(extra=()):
    """Resources folders of the Max installs gencheck can find: Max.app, the Max inside Ableton Live (Max for Live),
    Max in Program Files on Windows, and the install that holds the --gen-ref refpages"""
    out = list(extra)
    out += sorted(glob.glob("/Applications/Max*.app/Contents/Resources"), reverse=True)
    out += sorted(glob.glob("/Applications/Ableton Live*.app/Contents/App-Resources/Max/Max.app/Contents/Resources"),
                  reverse=True)
    pf = os.environ.get("ProgramFiles") or "C:/Program Files"
    out += sorted(glob.glob(os.path.join(glob.escape(pf), "Cycling '74", "Max*", "resources")), reverse=True)
    seen, res = set(), []
    for r in out:
        if os.path.isdir(r) and os.path.normcase(os.path.abspath(r)) not in seen:
            seen.add(os.path.normcase(os.path.abspath(r)))
            res.append(r)
    return res


def resources_of(path):
    """the Resources folder of the Max install that holds path (e.g. the --gen-ref refpages), or None"""
    d = os.path.abspath(path) if path else None
    while d and os.path.dirname(d) != d:
        if os.path.basename(d).lower() == "resources":
            return d
        d = os.path.dirname(d)
    return None


def max_library_index(extra=()):
    """({file name (lower case): path}, [Max install Resources folders searched]) of the *.genexpr files in places
    Max searches by default: every folder of the installed packages (of the Max install and ~/Documents/Max 9|8),
    the Max Examples folder and the user Library. Built once per run"""
    key = tuple(extra)
    if key not in _LIB_INDEX:
        apps = max_app_resources(extra)
        roots = []
        for res in apps:
            roots += [os.path.join(res, "C74", "packages"), os.path.join(res, "Examples"), os.path.join(res, "packages"),
                      os.path.join(res, "examples")]
        home = os.path.expanduser("~")
        for docs in (os.path.join(home, "Documents"), os.path.join(home, "OneDrive", "Documents")):
            for v in ("Max 9", "Max 8"):
                roots += [os.path.join(docs, v, "Packages"), os.path.join(docs, v, "Library")]
        idx = {}
        for r in roots:
            for dirpath, _dirs, files in os.walk(r):
                for f in files:
                    if f.lower().endswith(".genexpr"):
                        old = idx.get(f.lower())
                        if old is None or (rnbo_internal(old) and not rnbo_internal(os.path.join(dirpath, f))):
                            idx[f.lower()] = os.path.join(dirpath, f)   # a copy outside RNBO's internals wins
        _LIB_INDEX[key] = (idx, apps)
    return _LIB_INDEX[key]


def rnbo_internal(path):
    """a file inside the RNBO package's internal folders (server/node_modules): gen~ require() does not find it there
    (probe R1121)"""
    return bool(re.search(r"[/\\]RNBO[/\\].*node_modules", path))


def dir_index(d, limit=50000):
    """{file name (lower case): path} of the *.genexpr and *.gendsp files in folder d and its subfolders (like a
    folder added to Max's search path with subfolders). Hidden folders are skipped"""
    key = os.path.abspath(d)
    if key not in _DIR_INDEX:
        idx, n = {}, 0
        for dirpath, dirs, files in os.walk(d):
            dirs[:] = sorted(x for x in dirs if not x.startswith("."))
            for f in files:
                n += 1
                if f.lower().endswith((".genexpr", ".gendsp")):
                    idx.setdefault(f.lower(), os.path.join(dirpath, f))
            if n > limit:
                break
        _DIR_INDEX[key] = idx
    return _DIR_INDEX[key]


def find_library(lib, search_dirs, gen_path=(), extra=()):
    """path of a require()'d library: next to the file (search_dirs), in a --gen-path folder or its subfolders, or in
    Max's own folders; else None"""
    cands = (lib, lib + ".genexpr")
    for d in search_dirs:
        for cand in cands:
            path = os.path.join(d, cand)
            if os.path.isfile(path):
                return path
    for d in gen_path:
        for cand in cands:
            path = dir_index(d).get(os.path.basename(cand).lower())
            if path:
                return path
    idx = max_library_index(extra)[0]
    for cand in cands:
        path = idx.get(os.path.basename(cand).lower())
        if path:
            return path
    return None


def gen_context(items, search_dirs, gen_path=(), extra=()):
    """gen abstractions (*.gendsp) and require()'d GenExpr libraries found in search_dirs, the --gen-path folders
    (with subfolders) or Max's own folders"""
    abstractions, lib_funcs, missing, broken = set(), {}, [], []
    for d in search_dirs:
        for f in glob.glob(os.path.join(glob.escape(d), "*.gendsp")):
            abstractions.add(os.path.splitext(os.path.basename(f))[0])
    for d in gen_path:
        abstractions |= {os.path.splitext(os.path.basename(p))[0] for p in dir_index(d).values()
                         if p.lower().endswith(".gendsp")}
    # a library may require other libraries (9.2.0 runs that: probe R1401; 9.1.4 does not). Their functions are
    # marked nested; a missing nested library is only noted for the codebox's require line
    todo = [(n.lib, n.line, None, search_dirs) for n in items if is_require(n)]
    seen = set()
    while todo:
        lib, line, via, dirs = todo.pop(0)
        path = find_library(lib, dirs, gen_path, extra)
        if path is None:
            if via is None:
                missing.append((line, lib, None))
            continue
        if rnbo_internal(path):
            if via is None:
                missing.append((line, lib, path))       # found only in RNBO's internal folder: gen~ does not look there
            continue
        if path in seen:
            continue                                     # required twice: loaded once (probe R458)
        seen.add(path)
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as f:   # a BOM in a library is fine (probe R457)
                lib_src = f.read()
            internal = False
            for m in Parser(tokenize(lib_src)).program():
                if m.kind == "func":
                    m.lib, m.req_line, m.internal = os.path.basename(path), line, internal
                    m.nested = via                       # None, or the library that required this one
                    lib_funcs.setdefault(m.name, m)
                elif is_require(m):
                    todo.append((m.lib, line, os.path.basename(path), (os.path.dirname(path),) + tuple(dirs)))
        except OSError as e:
            if via is None:
                broken.append((line, lib, os.path.basename(path), "cannot be read (%s)" % e.strerror))
        except ParseError as e:
            if via is None:
                broken.append((line, lib, os.path.basename(path), "does not parse: %s (line %d of the library)"
                               % (str(e).rstrip("."), e.line)))
    return abstractions, lib_funcs, missing, broken


VERSION_RE = re.compile(r"[vV]?(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def parse_version(text):
    """'9.2.0' -> (9, 2, 0), '8' -> (8, 0, 0), 'v9.1.4' -> (9, 1, 4); unknown -> a high version, so the newest Max
    rules apply"""
    m = VERSION_RE.match((text or "").strip())
    return tuple(int(x or 0) for x in m.groups()) if m else (99, 0, 0)


def io_summary(src):
    """highest inlet / outlet number used; bare in / out count as in1 / out1 (probe R954)"""
    try:
        names = [t.text for t in tokenize(src) if t.kind == "id"]
    except ParseError:
        names = re.findall(r"[A-Za-z_]\w*", strip_comments(src))
    ins = [int(x[2:]) if x != "in" else 1 for x in names if re.fullmatch(r"in(\d+)?", x)]
    outs = [int(x[3:]) if x != "out" else 1 for x in names if re.fullmatch(r"out(\d+)?", x)]
    return {"in": max(ins) if ins else 0, "out": max(outs) if outs else 0}


class NotText(Exception):
    pass


def read_source(path):
    """(text, findings) of a codebox file. A UTF-8 BOM is taken off and reported as G506: harmless if only the saved
    file has it, but a codebox whose text starts with U+FEFF fails at load (probes R507, R687, R867). UTF-16 files
    (Windows 'Unicode', PowerShell 5.1 '>') are decoded: Max never sees the file encoding. Raises OSError, NotText"""
    with open(path, "rb") as f:
        data = f.read()
    notes = []
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = data.decode("utf-16", errors="replace")
    elif b"\x00" in data:
        head = data[:400]
        even, odd = head[0::2].count(0), head[1::2].count(0)
        if odd > len(head) // 4 and even == 0:
            text = data.decode("utf-16-le", errors="replace")
        elif even > len(head) // 4 and odd == 0:
            text = data.decode("utf-16-be", errors="replace")
        else:
            raise NotText("%s is not a text file (it has NUL bytes)" % path)
    else:
        text = data.decode("utf-8", errors="replace")
    if text.startswith("\ufeff"):
        text = text[1:]
        notes.append({"rule": "G506", "sev": "warn", "line": 1,
                      "msg": "the file starts with a byte order mark (BOM, U+FEFF). Harmless if only the saved file has it; "
                             "if the codebox text itself starts with it, Max refuses the codebox at load without naming "
                             "the character (probes R507, R687, R867). Save the file as UTF-8 without BOM"})
    return text, notes


PATCHER_EXT = (".maxpat", ".gendsp", ".maxhelp", ".json")


def patcher_codeboxes(j, gendsp=False, groups=None):
    """code of the gen~ codeboxes in a Max patcher (parsed JSON): codeboxes in patchers with classnamespace dsp.gen,
    in a .gendsp, or inside an older gen~ box whose patcher has no classnamespace. jit.gen / jit.pix / RNBO code is
    left out (another language). groups, if given, gets one id per codebox: the same id for codeboxes of the same
    gen patcher"""
    out = []

    def walk(o, dom, gp):
        if isinstance(o, dict):
            ns = o.get("classnamespace")
            if ns == "dsp.gen":
                dom, gp = "dsp", id(o)
            elif ns in ("jit.gen", "rnbo"):
                dom = "other"
            if o.get("maxclass") == "codebox" and isinstance(o.get("code"), str) and dom == "dsp":
                out.append(o["code"].replace("\r\n", "\n").replace("\r", "\n"))
                if groups is not None:
                    groups.append(gp)
            txt = o.get("text") if isinstance(o.get("text"), str) else ""
            for k, v in o.items():
                d2, g2 = dom, gp
                if k == "patcher" and isinstance(v, dict) and not v.get("classnamespace"):
                    if re.match(r"(mc\.|mcs\.)?gen~(\s|$)", txt):
                        d2, g2 = "dsp", id(v)
                    elif re.match(r"jit\.(gen|pix|gl\.pix)|rnbo~", txt):
                        d2 = "other"
                walk(v, d2, g2)
        elif isinstance(o, list):
            for v in o:
                walk(v, dom, gp)
    walk(j, "dsp" if gendsp else None, id(j))
    return out


def param_names(src):
    """names of the Params declared at the top of a codebox (Param a(0), b;)"""
    try:
        items = Parser(tokenize(src)).program()
    except (ParseError, RecursionError):     # very deep code: check_source retries it with a big stack, not here
        return set(re.findall(r"^\s*Param\s+([^\W\d]\w*)", strip_comments(src), re.M))
    return {it[0] for n in items if n.kind == "decl" and n.kw == "Param" for it in n.items}


def file_units(path):
    """[(label, code, findings from reading, sibling Params)] of a file: one unit for codebox text, one per gen~
    codebox for a Max patcher (.maxpat, .gendsp, .maxhelp). Sibling Params: names declared as Param in the other
    codeboxes of the same gen patcher and not in this one; a gen patcher's Params are shared by its codeboxes, like a
    [param] box (gencheck passes them like --param). Raises OSError, NotText"""
    if path.lower().endswith(".amxd"):
        raise NotText("%s is a Max for Live device: open it in Max and save or copy the codebox text" % path)
    src, notes = read_source(path)
    name = os.path.basename(path)
    if path.lower().endswith(PATCHER_EXT) or (src.lstrip().startswith("{") and '"patcher"' in src[:2000]):
        try:
            j = json.loads(src)
        except ValueError:
            j = None
        if not (isinstance(j, dict) and isinstance(j.get("patcher"), dict)) and \
                path.lower().endswith((".maxpat", ".gendsp", ".maxhelp")):
            raise NotText("%s is not a Max patcher (no patcher JSON in it)" % path)
        if isinstance(j, dict) and isinstance(j.get("patcher"), dict):
            groups = []
            codes = patcher_codeboxes(j, path.lower().endswith(".gendsp"), groups)
            own = [param_names(c) for c in codes]
            units = []
            for k, c in enumerate(codes):
                sib = set()
                for m in range(len(codes)):
                    if m != k and groups[m] == groups[k]:
                        sib |= own[m]
                units.append(("%s [codebox %d]" % (name, k + 1), c, [], tuple(sorted(sib - own[k]))))
            return units
    return [(name, src, notes, ())]


ISSUE_URL_MAX = 7500          # longer issue links get cut; then the draft is pasted by hand
MAX_OUT_GAPS = 64            # above this output number, one G131 finding instead of one per gap
MAX_IO_WRITE = 256           # --write-gendsp refuses more inlets or outlets (an inN / outN typo)

GENDSP_APPVERSION = {"major": 9, "minor": 1, "revision": 4, "architecture": "x64", "modernui": 1}


def gendsp_patcher(code, nin, nout):
    """a gen patcher (.gendsp) holding one codebox wired to [in 1..nin] and [out 1..nout]. Same form as the probe
    files of maxprobe/make_probes.py, which Max 9.1.4 and 9.2.0 loaded with [gen~ @gen NAME] for every probe"""
    nin, nout = max(1, nin), max(1, nout)
    boxes = [{"box": {"code": code.rstrip("\n").replace("\r\n", "\n").replace("\n", "\r\n"), "fontface": 0,
                      "fontname": "<Monospaced>", "fontsize": 12.0, "id": "obj-code", "maxclass": "codebox",
                      "numinlets": nin, "numoutlets": nout, "outlettype": [""] * nout,
                      "patching_rect": [20.0, 60.0, 600.0, 400.0]}}]
    lines = []
    for k in range(1, nin + 1):
        boxes.append({"box": {"id": "obj-in%d" % k, "maxclass": "newobj", "numinlets": 0, "numoutlets": 1,
                              "outlettype": [""], "patching_rect": [20.0 + 50 * (k - 1), 20.0, 40.0, 22.0],
                              "text": "in %d" % k}})
        lines.append({"patchline": {"destination": ["obj-code", k - 1], "source": ["obj-in%d" % k, 0]}})
    for k in range(1, nout + 1):
        boxes.append({"box": {"id": "obj-out%d" % k, "maxclass": "newobj", "numinlets": 1, "numoutlets": 0,
                              "patching_rect": [20.0 + 50 * (k - 1), 480.0, 45.0, 22.0], "text": "out %d" % k}})
        lines.append({"patchline": {"destination": ["obj-out%d" % k, 0], "source": ["obj-code", k - 1]}})
    return {"patcher": {"fileversion": 1, "appversion": GENDSP_APPVERSION, "classnamespace": "dsp.gen",
                        "rect": [100.0, 100.0, 660.0, 540.0], "boxes": boxes, "lines": lines}}


def made_by_gencheck(path):
    """True if the .gendsp at path is exactly what gendsp_patcher() writes for the code it holds, so it may be
    replaced. A file saved by Max (which adds keys such as openrect) or changed otherwise is not"""
    try:
        with open(path, encoding="utf-8") as f:
            j = json.load(f)
        boxes = [b["box"] for b in j["patcher"]["boxes"]]
        code = [b for b in boxes if b.get("id") == "obj-code"][0]["code"]
        nin = sum(1 for b in boxes if re.fullmatch(r"obj-in\d+", str(b.get("id"))))
        nout = sum(1 for b in boxes if re.fullmatch(r"obj-out\d+", str(b.get("id"))))
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
        return False
    return j == gendsp_patcher(code, nin, nout)


def write_gendsp(path, code, nin, nout):
    """write the codebox as a .gendsp; returns an error text or None. A file that gencheck did not write is kept"""
    if os.path.exists(path) and not made_by_gencheck(path):
        return ("%s exists and was not written by gencheck, or was changed or saved in Max since: choose another name"
                % path)
    if nout > MAX_IO_WRITE or nin > MAX_IO_WRITE:
        return "%d inlets and %d outlets: check the inN / outN numbers (not written)" % (nin, nout)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(gendsp_patcher(code, nin, nout), f, indent=1, ensure_ascii=False)
    except OSError as e:
        return str(e)
    return None


def check_source(src, ref, old_src=None, io=None, search_dirs=(), max_version=None, patcher_params=(), gen_path=(),
                 patcher_complete=False):
    """(findings, summary). search_dirs: folders searched for libraries and abstractions (the checked file's own
    folder); gen_path: folders searched with their subfolders (--gen-path). patcher_params: names of the gen
    patcher's [param] boxes, which the codebox may read bare. patcher_complete: patcher_params names every [param],
    [history], [data] and [buffer] box of the gen patcher, so another name the code reads is not defined anywhere. Does not raise on odd input: very deep nesting is
    retried in a thread with a big stack; if that still overflows, the code is reported as not checked (G505)"""
    args = (src, ref, old_src, io, search_dirs, max_version, tuple(patcher_params), tuple(gen_path), patcher_complete)
    try:
        return _check_source(*args)
    except RecursionError:
        pass
    box = {}

    def work():
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(200000)
        try:
            box["r"] = _check_source(*args)
        except RecursionError:
            box["r"] = None
        finally:
            sys.setrecursionlimit(old)

    old_size = threading.stack_size()
    try:
        for size in (512 * 1024 * 1024, 0x0FF00000, 64 * 1024 * 1024):
            try:
                threading.stack_size(size)
                break
            except (RuntimeError, ValueError):     # Windows refuses 256 MiB and more
                continue
        try:
            t = threading.Thread(target=work)
            t.start()
            t.join()
        except (RuntimeError, MemoryError):
            box["r"] = None
    finally:
        threading.stack_size(old_size)
    if box.get("r") is not None:
        return box["r"]
    return ([{"rule": "G505", "sev": "warn", "line": 0,
              "msg": "the code is nested too deeply for gencheck (very long else-if chain or expression); it was not checked"}],
            io_summary(src))


def _check_source(src, ref, old_src=None, io=None, search_dirs=(), max_version=None, patcher_params=(), gen_path=(),
                  patcher_complete=False):
    findings = []
    raw = src.encode("utf-8", errors="replace")
    if len(raw) > BIG_FILE:
        findings.append({"rule": "G502", "sev": "info", "line": 0,
                         "msg": "file is %d bytes. A codebox of about 150 KB of plain statements compiled and ran on "
                                "Max 9.1.4 and 9.2.0 (probe R1250), so size alone is not known to break it. In real use "
                                "one codebox of about 105 KB went silent with no error message (the cause was never "
                                "shown); if the gen~ is silent, try splitting the code" % len(raw)})
    nonascii = sum(1 for ch in src if ord(ch) > 127)
    if nonascii:
        line = next(i for i, l in enumerate(src.split("\n"), 1) if any(ord(ch) > 127 for ch in l))
        findings.append({"rule": "G503", "sev": "info", "line": line, "msg": "%d non-ASCII characters (first at line %d)" % (nonascii, line)})
    rates = [i for i, l in enumerate(re.sub(r"//[^\n]*", "", src).split("\n"), 1) if re.search(r"(?<![\w.])(44100|48000|88200|96000)(\.0*)?(?![\w.])", l)]
    if rates:
        findings.append({"rule": "G411", "sev": "info", "line": rates[0],
                         "msg": "sample rate written as a number on %d line(s) (first %d). Use samplerate / dim()" % (len(rates), rates[0])})
    summary = io_summary(src)
    if io is not None and (summary["in"] != io[0] or summary["out"] != io[1]):
        findings.append({"rule": "G504", "sev": "warn", "line": 0,
                         "msg": "code uses in1..in%d and out1..out%d but you said %d in / %d out" % (summary["in"], summary["out"], io[0], io[1])})
    notes = []
    try:
        parser = Parser(tokenize(src, notes))
        items = parser.program()
    except ParseError as e:
        findings.append({"rule": "G100", "sev": "error", "line": e.line, "msg": str(e)})
        return findings, summary
    findings += notes + parser.notes
    if items and getattr(items[0], "implicit", False) and items[0].kind == "expr":
        summary["out"] = max(summary["out"], 1)       # a lone bare expression goes to out1 (probe R952)
    old_idents = old_decls = None
    if old_src is not None:
        old_idents, old_decls = idents_and_decls(old_src)
    extra = tuple(r for r in (resources_of(ref.path) if ref else None,) if r)
    abstractions, lib_funcs, missing, broken = gen_context(items, search_dirs, gen_path, extra)
    an = Analyzer(items, ref, old_idents, old_decls, abstractions, lib_funcs, max_version, patcher_params,
                  patcher_complete)
    for line, lib, base, why in broken:
        findings.append({"rule": "G123", "sev": "warn", "line": line,
                         "msg": "require(\"%s\"): the library %s %s. Max checks a require()'d file at load even when "
                                "nothing from it is called (a missing one fails: probes R456, R697). A library that does "
                                "not parse compiled on Max 9.1.4 and 9.2.0 when nothing from it was called (probe "
                                "R1400); calling one of its functions was not measured. Fix the library; its functions "
                                "are not checked here"
                                % (lib, base, why)})
    an.missing_libs = missing + broken
    apps = max_library_index(extra)[1] if missing else []
    for line, lib, internal in missing:
        base = lib if lib.lower().endswith(".genexpr") else lib + ".genexpr"
        if internal:
            findings.append({"rule": "G117", "sev": "error", "line": line,
                             "msg": "require(\"%s\"): %s exists only inside the RNBO package's internal folder (%s), "
                                    "where gen~ does not look: Max 9.1.4 and 9.2.0 refuse the codebox like a missing "
                                    "file (probe R1121; Max: 'unable to find .genexpr include file %s', probes R456, "
                                    "R697). Copy the file next to the patch or into a folder of Max's search path"
                                    % (lib, base, os.path.dirname(internal)[internal.find("RNBO"):], lib)})
        elif apps:
            findings.append({"rule": "G117", "sev": "error", "line": line,
                             "msg": "require(\"%s\"): %s is not next to the file, in --gen-path, or in the packages, "
                                    "Examples or Library folders of %s. Max: 'unable to find .genexpr include file %s' "
                                    "and the gen~ is not built (probes R456, R697). If the file is in another folder of "
                                    "Max's search path, pass that folder with --gen-path"
                                    % (lib, base, " and ".join(short(a, 70) for a in apps[:2]), lib)})
        else:
            findings.append({"rule": "G117", "sev": "warn", "line": line,
                             "msg": "require(\"%s\"): %s is not next to the file or in --gen-path, and gencheck found no "
                                    "Max install whose packages, Examples and Library folders it could search. If Max "
                                    "cannot find it either: 'unable to find .genexpr include file %s', and the gen~ is "
                                    "not built (probes R456, R697). Pass the library's folder with --gen-path, or the "
                                    "Max install with --gen-ref" % (lib, base, lib)})
    findings += an.run()
    try:
        flow_decls = dict(an.decls)
        for name in patcher_params:
            flow_decls.setdefault(name, ("Param", 0, [], {}))   # a patcher param: range unknown
        flow = genflow.Flow(items, flow_decls, funcs={k: v for k, v in an.funcs.items() if not an.op_named(k)})
        g401 = flow.interp_findings()
        notes = flow.notes
    except RecursionError:
        raise
    except Exception as e:  # the flow analysis is a heuristic: never let it stop the other checks
        g401, notes = [], []
        findings.append({"rule": "G400", "sev": "warn", "line": 0,
                         "msg": "gencheck's flow analysis failed (internal error %s, please report it with the file), so "
                                "G401 (runaway buffer index) was not checked in this file" % type(e).__name__})
    for line, what, mode, why, part, (bmode, dflt) in g401:
        findings.append({"rule": "G401", "sev": "warn", "line": line,
                         "msg": "%s(interp=%s) %s can run away to inf or huge values (%s), and the code does not limit "
                                "it before the read. Its boundmode is \"%s\"%s. With an inf index Max 9.1.4 and 9.2.0 "
                                "read nan (peek with clamp or ignore, lookup: probes R1240-R1242), and the nan then "
                                "spreads; a finite index past 2^31 with boundmode wrap reads the right sample (probe "
                                "R1243). An interpolated read with a runaway index crashed Max in real use, and wrap() "
                                "does not stop it (wrap(inf, 0, 1) is nan, phasor(inf) is inf: probes R497, R498). Clamp "
                                "the value before wrap() or phasor(), e.g. wrap(clamp(x, -1e9, 1e9), lo, hi)"
                                % (what, mode, part, why, bmode, " (the default for %s)" % what.split(".")[-1] if dflt
                                   else "")})
    for line, msg in notes:
        findings.append({"rule": "G400", "sev": "info", "line": line,
                         "msg": "flow analysis could not read this statement (%s); G401 not checked here" % msg})
    findings.sort(key=lambda f: (f["line"], f["rule"]))
    return findings, summary


def show(label, fnd, summ, args):
    """print one checked unit (unless --json); returns its exit code: 1 for an error (or a warn with --strict)"""
    cnt = {s: sum(1 for x in fnd if x["sev"] == s) for s in ("error", "warn", "info")}
    code = 1 if cnt["error"] or (args["strict"] and cnt["warn"]) else 0
    if args["json"]:
        return code
    print("%s: %d error, %d warn, %d info | uses %d in, %d out | static check only, not compiled"
          % (label, cnt["error"], cnt["warn"], cnt["info"], summ["in"], summ["out"]))
    shown = {}
    for x in fnd:
        if x["sev"] == "info" and not args["info"]:
            continue
        shown[x["rule"]] = shown.get(x["rule"], 0) + 1
        if args["max"] and shown[x["rule"]] > args["max"]:
            continue
        print("  L%-5d %-5s %s %s" % (x["line"], x["sev"], x["rule"], x["msg"]))
    for r, n in sorted(shown.items()):
        if args["max"] and n > args["max"]:
            print("  ...    %s: %d more" % (r, n - args["max"]))
    return code


def main(argv):
    args, files = {"strict": False, "info": False, "json": False, "max": 5, "old": None, "io": None, "ref": None, "path": [],
                   "maxver": None, "params": [], "complete": False, "log": None, "mismatch": None, "logcode": False,
                   "logmode": None, "gendsp": None}, []
    i = 0
    try:
        while i < len(argv):
            a = argv[i]
            if a in ("-h", "--help"):
                print(__doc__)
                return 0
            elif a == "--strict":
                args["strict"] = True
            elif a == "--info":
                args["info"] = True
            elif a == "--json":
                args["json"] = True
            elif a == "--old":
                args["old"] = argv[i + 1]; i += 1
            elif a == "--io":
                args["io"] = (int(argv[i + 1]), int(argv[i + 2])); i += 2
                if min(args["io"]) < 0:
                    raise ValueError("--io needs two counts of 0 or more")
            elif a == "--max-version":
                if not VERSION_RE.fullmatch(argv[i + 1].strip()):
                    raise ValueError("--max-version needs a version like 9.2.0, got %r" % argv[i + 1])
                args["maxver"] = argv[i + 1].strip().lstrip("vV"); i += 1
            elif a == "--gen-path":
                if not os.path.isdir(argv[i + 1]):
                    raise ValueError("--gen-path %s is not a folder" % argv[i + 1])
                args["path"].append(argv[i + 1]); i += 1
            elif a == "--gen-ref":
                args["ref"] = argv[i + 1]; i += 1
            elif a == "--param":
                if not re.fullmatch(r"[^\W\d]\w*", argv[i + 1]):
                    raise ValueError("--param needs a name, got %r" % argv[i + 1])
                args["params"].append(argv[i + 1]); i += 1
            elif a == "--complete-params":
                args["complete"] = True
            elif a == "--log":
                args["log"] = argv[i + 1]; i += 1
            elif a == "--log-mismatch":
                args["mismatch"] = argv[i + 1]; i += 1
            elif a == "--log-code":
                args["logcode"] = True
            elif a in ("--log-summary", "--log-mark-sent"):
                args["logmode"] = a
            elif a == "--write-gendsp":
                if not argv[i + 1].lower().endswith(".gendsp"):
                    raise ValueError("--write-gendsp needs a file name ending in .gendsp, got %r" % argv[i + 1])
                args["gendsp"] = argv[i + 1]; i += 1
            elif a == "--max-per-rule":
                args["max"] = int(argv[i + 1]); i += 1
                if args["max"] < 0:
                    raise ValueError("--max-per-rule needs 0 (all) or more")
            elif a.startswith("-"):
                raise ValueError(a)
            else:
                files.append(a)
            i += 1
    except (IndexError, ValueError) as e:
        print("gencheck: bad arguments (%s). See --help" % e, file=sys.stderr)
        return 2
    if args["logmode"] or args["mismatch"] or args["logcode"]:
        if not args["log"]:
            print("gencheck: %s needs --log FILE" % (args["logmode"] or ("--log-mismatch" if args["mismatch"] else "--log-code")),
                  file=sys.stderr)
            return 2
    if args["logmode"]:
        return log_summary(args["log"], mark=args["logmode"] == "--log-mark-sent")
    if not files:
        print(__doc__)
        return 2
    if args["gendsp"] and (len(files) != 1 or files[0].lower().endswith(PATCHER_EXT)):
        print("gencheck: --write-gendsp needs exactly one file of codebox text (.genexpr, .txt)", file=sys.stderr)
        return 2
    if args["gendsp"] and args["params"]:
        print("gencheck: --write-gendsp writes a gen patcher with only the codebox and in/out boxes; the [param] boxes "
              "named by --param would be missing. Declare them in the code as Param, or leave out --param",
              file=sys.stderr)
        return 2
    if args["mismatch"] is not None and len(files) != 1:
        print("gencheck: --log-mismatch needs exactly one file (the smallest code that shows the problem)", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # a Windows console or pipe may not take every character
    for what, val in (("--gen-ref", args["ref"]), ("GENCHECK_GEN_REF", os.environ.get("GENCHECK_GEN_REF"))):
        if val and not (os.path.isdir(os.path.join(val, "common")) and os.path.isdir(os.path.join(val, "dsp"))):
            print("gencheck: %s %s is not a Gen refpages folder (it needs common/ and dsp/)" % (what, val), file=sys.stderr)
            return 2
    # the Max version to judge by: --max-version, else the Max the user started last (Max's log), else the install
    started = None if args["maxver"] else last_started_max()
    maxver = args["maxver"] or (started[0] if started else None)
    refdir = find_ref(args["ref"], prefer=maxver)
    ref = GenRef(refdir)
    if args["maxver"]:
        source = "option"
    elif started:
        source = "max log"
    else:
        maxver = ref.max_version() if ref else None
        source = "install" if maxver else "none"
    if not args["json"]:
        print({"option": "judged as Max %s (--max-version)" % maxver,
               "max log": "judged as Max %s: the Max started last (%s). Another version: --max-version"
                          % (maxver, started[1] if started else ""),
               "install": "judged as Max %s: the Max install found. Another version: --max-version" % maxver,
               "none": "judged by the Max 9.2.0 rules: no Max version found. Another version: --max-version"}[source])
    try:
        old_src = read_source(args["old"])[0] if args["old"] else None
    except (OSError, NotText) as e:
        print("gencheck: --old: %s" % e, file=sys.stderr)
        return 2
    worst, report = 0, []
    if not ref and not args["json"]:
        print("gencheck: Gen reference not found (no Max install?). Unknown-function, argument-count and operator-name "
              "checks are skipped (G105, G106, G303, G304; G108 only for noise). Constants, globals and history() use "
              "names measured in Max. Use --gen-ref DIR.")
    for f in files:
        try:
            units = file_units(f)
        except (OSError, NotText) as e:      # keep going: the other files are still checked, --json stays valid
            print("gencheck: %s" % e, file=sys.stderr)
            report.append({"file": f, "error": str(e), "summary": None, "findings": []})
            worst = max(worst, 2)
            continue
        if not units:
            report.append({"file": f, "codeboxes": 0, "summary": None, "findings": []})
            if not args["json"]:
                print("%s: no gen~ codebox found (jit.gen, jit.pix and RNBO code is not checked)" % os.path.basename(f))
        if args["gendsp"] and (len(units) != 1 or units[0][0] != os.path.basename(f)):
            print("gencheck: --write-gendsp needs codebox text, and %s holds a patcher" % f, file=sys.stderr)
            return 2
        for k, (label, src, read_notes, sibling_params) in enumerate(units):
            entry = {"file": f}
            if label != os.path.basename(f):
                entry["codebox"] = k + 1
            try:
                fnd, summ = check_source(src, ref, old_src, args["io"], [os.path.dirname(os.path.abspath(f))],
                                         maxver, args["params"] + list(sibling_params), args["path"],
                                         args["complete"])
                fnd = read_notes + fnd
            except Exception as e:  # a gencheck bug: say so, and keep it apart from "the code has errors" (exit 1)
                msg = "internal error %s: %s (please report it with the file)" % (type(e).__name__, e)
                print("gencheck: %s: %s" % (label, msg), file=sys.stderr)
                entry.update({"internal_error": msg, "summary": None, "findings": []})
                report.append(entry)
                worst = max(worst, 3)
                continue
            entry.update({"summary": summ, "findings": fnd})
            report.append(entry)
            worst = max(worst, show(label, fnd, summ, args))
            if args["gendsp"]:
                gname = os.path.splitext(os.path.basename(args["gendsp"]))[0]
                if any(x["sev"] == "error" for x in fnd):
                    msg = "%s not written: fix the errors first" % args["gendsp"]
                else:
                    err = write_gendsp(args["gendsp"], src, summ["in"], summ["out"])
                    msg = ("gencheck: %s" % err) if err else (
                        "wrote %s: put it next to your saved patch and use [gen~ @gen %s] (or paste the code into a "
                        "codebox)" % (args["gendsp"], gname))
                    if err:
                        worst = max(worst, 2)
                entry["gendsp"] = msg
                if not args["json"]:
                    print(msg)
    if args["json"]:
        print(json.dumps({"version": VERSION, "gen_ref": refdir, "max_version": maxver, "max_version_source": source,
                          "files": report}, indent=1))
    if args["log"]:
        log_run(args, report, maxver)
    return worst


# ----------------------------------------------------------------- local log (feedback, never sent by gencheck)

def log_run(args, report, maxver):
    """append one line to the local log: counts and rule IDs only, no code and no file names, unless --log-mismatch
    (the user says Max did something else) and --log-code (the user agreed to keep the code)"""
    rules, errs, warns, units = {}, 0, 0, 0
    for e in report:
        for x in e.get("findings") or []:
            rules[x["rule"]] = rules.get(x["rule"], 0) + 1
            errs += x["sev"] == "error"
            warns += x["sev"] == "warn"
        units += e.get("summary") is not None
    import datetime
    entry = {"t": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "kind": "run",
             "gencheck": VERSION, "max": maxver or "unknown", "codeboxes": units, "errors": errs, "warns": warns,
             "rules": dict(sorted(rules.items()))}
    if args["mismatch"] is not None:
        f = report[0] if report else {}
        entry.update({"kind": "mismatch", "max_said": args["mismatch"][:2000], "sent": False,
                      "findings": [{"rule": x["rule"], "sev": x["sev"], "line": x["line"]} for x in f.get("findings") or []]})
        if args["logcode"] and report:
            try:
                entry["code"] = read_source(f["file"])[0][:20000]
            except (OSError, NotText):
                pass
    try:
        d = os.path.dirname(os.path.abspath(args["log"]))
        os.makedirs(d, exist_ok=True)
        with open(args["log"], "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        print("gencheck: --log: %s" % e, file=sys.stderr)


def log_summary(path, mark=False):
    """--log-summary: counts and a draft issue for the mismatch reports not sent yet. --log-mark-sent: mark them sent
    (after the user submitted the issue). Nothing is sent from here"""
    try:
        entries = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    except FileNotFoundError:
        entries = []
    except (OSError, ValueError) as e:
        print("gencheck: --log: %s" % e, file=sys.stderr)
        return 2
    todo = [e for e in entries if e.get("kind") == "mismatch" and not e.get("sent")]
    if mark:
        for e in todo:
            e["sent"] = True
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries))
        print("gencheck log: %d mismatch report(s) marked as sent" % len(todo))
        return 0
    runs = sum(1 for e in entries if e.get("kind") == "run")
    print("gencheck log %s: %d runs, %d mismatch report(s) not sent" % (path, runs, len(todo)))
    if not todo:
        return 0
    lines = ["gencheck %s disagreed with Max in %d case(s)." % (VERSION, len(todo)), ""]
    link_lines = list(lines)
    has_code = False
    for k, e in enumerate(todo, 1):
        found = ", ".join("%s %s L%d" % (x["rule"], x["sev"], x["line"]) for x in e.get("findings", [])) or "nothing"
        head = ["%d. Max %s, gencheck %s (%s)" % (k, e.get("max"), e.get("gencheck"), e.get("t", "")[:10]),
                "   Max said: %s" % e.get("max_said", ""), "   gencheck said: %s" % found]
        lines += head
        link_lines += head
        if e.get("code"):
            has_code = True
            lines += ["", "```", e["code"].rstrip(), "```"]
            link_lines += ["", "(code of case %d: paste here the part you want to share, or leave it out)" % k]
        lines.append("")
        link_lines.append("")
    body = "\n".join(lines)
    link_body = "\n".join(link_lines)          # the link never carries code: the user pastes what they choose
    print("\n--- draft issue (review it; remove code you do not want to publish) ---\n" + body)
    if ISSUE_REPO:
        from urllib.parse import quote
        title = quote("gencheck disagreed with Max (%d case%s)" % (len(todo), "" if len(todo) == 1 else "s"))
        base = "https://github.com/%s/issues/new?labels=mismatch&title=%s&body=" % (ISSUE_REPO, title)
        what = ("the form holds the text above without its code; paste the code you want to share" if has_code
                else "the form holds the text above")
        if len(base) + len(quote(link_body)) <= ISSUE_URL_MAX:
            print("\n--- issue link (%s; nothing is posted until you press Submit) ---\n%s"
                  % (what, base + quote(link_body)))
        else:   # a long link is cut by browsers or GitHub: never send a shorter text than the draft above
            print("\n--- the draft is too long for a link: open this empty form and paste the parts of the draft "
                  "above you want to share (nothing is posted until you press Submit) ---\n" + base)
    else:
        print("\n(the public repository is not set yet: copy the text above into a new issue)")
    return 0


class _PipeOut:
    """stdout that goes quiet when the reader closes the pipe (gencheck ... | head): no traceback, and the exit code
    still says whether errors were found"""

    def __init__(self, f):
        self.f, self.gone = f, False

    def write(self, s):
        if not self.gone:
            try:
                return self.f.write(s)
            except BrokenPipeError:
                self.close_pipe()
        return len(s)

    def flush(self):
        if not self.gone:
            try:
                self.f.flush()
            except BrokenPipeError:
                self.close_pipe()

    def close_pipe(self):
        self.gone = True
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), self.f.fileno())
        except (OSError, ValueError):
            pass

    def __getattr__(self, k):
        return getattr(self.f, k)


if __name__ == "__main__":
    sys.stdout = _PipeOut(sys.stdout)
    rc = main(sys.argv[1:])
    sys.stdout.flush()
    sys.exit(rc)
