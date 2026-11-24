"""genflow - value flow and loop-gain analysis for GenExpr (used by gencheck.py, rule G401).

Why: an interpolated peek/sample whose index runs away (to inf, or past 2^31) reads outside the buffer; this
crashed Max in real use. wrap() does not protect the index: in Max 9.2.0 wrap(inf, 0, 1) gives nan and
phasor(inf) gives inf (probes R497, R498). The model follows two ways an index can run away:
  (a) an outside signal (inN), or
  (b) state that grows without limit: History feedback whose loop gain can exceed 1
      (for example a spring whose stiffness changes while it moves).
Other sources are not followed: log(0) and ftom(0) give -inf, exp(1000) gives inf (probes R486, R978, R496),
and a division by a value near 0 can be huge (x / 0 itself gives 0, probe R482). NaN is not tracked
(sqrt(-1), log(-1), wrap(inf) give nan); an inf index into peek(interp linear) with clamp or ignore, or into
lookup(), reads nan without a crash (probes R1240-R1242); a nan index itself was not measured.

Model:
- Only History carries a value from one sample to the next. Plain variables are recomputed every
  sample, so a read sees the assignment(s) that reach it in program order (if/else merge; in a loop a read also
  sees the assignments of the loop body that reach the end of the body: loop-carried values). 'a, b = x, y' pairs names and values in order.
- For each History H, the update is written as a function of the previous History values. Its
  coefficient on each History S in the same feedback group is computed with interval arithmetic
  (Params from their min/max, samplerate 22050..192000). If |coef| summed over the group can exceed 1
  for some member, the group may grow without limit (max-row-sum norm > 1), unless its coefficients are
  fixed numbers for each Param setting (a biquad or state-variable filter) and every setting tried gives a
  stable matrix (fixed_stable). Coefficients chosen by a condition (switching) are not fixed.
- Measured arithmetic: x / 0 and x % 0 are 0, pow(0, -1) is 0, a negative base with a non-integer exponent
  gives 0, t60(0) is 1 (probes R482, R484, R495, R487, R493); div, mod, switch are read as / % ?:.
- clamp, clip, sin, cos, tanh, noise, comparisons, fract and x - floor(x) cut the flow (bounded output).
  selector() gives 0 or one of its inputs (probes R971, R972). In 'x < C ? a : b' each branch is evaluated with
  the range of x the condition allows. A feedback group whose History ranges stay finite (history_ranges, with
  one widening step for capped growth) is safe whatever its coefficients.
  wrap, fold, phasor, triangle and x % m cut feedback growth but pass a runaway value on.
  min(x, C) / max(x, C) with finite C count as a cap.
- fixnan turns inf into 0 (probe R845) but passes huge finite values, so it is not a cap here.
- Values read back from Data / Delay / Buffer are assumed finite (not tracked). A user function body is walked
  for each call with its parameters bound to the arguments, so its buffer reads are checked; a History inside
  one is not. A call's result is unknown, so a feedback loop through a user function counts as unknown gain,
  and a runaway argument is assumed to reach the result.
"""
import itertools, math, re

INF = float("inf")
ZERO = (0.0, 0.0)
ONE = (1.0, 1.0)

BOUNDED_OUT = {"clamp", "clip", "sin", "cos", "tanh", "atan", "atan2", "fastsin", "fastcos", "cycle",
               "noise", "train", "fract", "sign", "step", "smoothstep", "gt", "gte", "lt", "lte", "eq",
               "neq", "gtp", "ltp", "gtep", "ltep", "eqp", "neqp", "and", "or", "not", "xor", "bool", "isnan",
               "isdenorm", "mc_channel", "dim", "channels", "wave", "sample", "lookup", "nearest", "peek", "elapsed"}
# bounded for finite input, so they stop feedback growth, but not for inf: wrap(inf) and fold(inf) give nan,
# phasor(inf) gives inf, triangle(inf) gives nan (probes R497, R844, R498, R976). The index is not safe behind them
WRAPPERS = {"wrap", "fold", "phasewrap", "phasor", "triangle"}
MAG_KEEP = {"fixdenorm", "fixnan", "abs", "neg", "int", "float", "floor", "ceil", "round", "trunc", "dcblock", "slide"}
CONSTS = {"pi": math.pi, "twopi": 2 * math.pi, "halfpi": math.pi / 2, "invpi": 1 / math.pi,
          "degtorad": math.pi / 180, "radtodeg": 180 / math.pi, "ln2": math.log(2), "ln10": math.log(10),
          "log2e": 1 / math.log(2), "log10e": 1 / math.log(10), "sqrt2": math.sqrt(2), "sqrt1_2": math.sqrt(0.5),
          "phi": (1 + math.sqrt(5)) / 2, "e": math.e, "E": math.e}
CONSTS.update({k.upper(): v for k, v in list(CONSTS.items())})
RANGES = {"samplerate": (22050.0, 192000.0), "vectorsize": (1.0, 4096.0), "voice": (0.0, 1e6),
          "voicecount": (1.0, 1e6), "mc_channel": (1.0, 1e4), "mc_channelcount": (1.0, 1e4)}
RANGES.update({k.upper(): v for k, v in list(RANGES.items())})
POINT_FUNCS = {"sin": math.sin, "cos": math.cos, "tan": math.tan, "tanh": math.tanh, "atan": math.atan,
               "sinh": math.sinh, "cosh": math.cosh, "asin": math.asin, "acos": math.acos, "fastsin": math.sin,
               "fastcos": math.cos, "fasttan": math.tan}
INTERP_DEFAULT = {"peek": "none", "sample": "linear", "wave": "linear", "lookup": "linear"}
BOUND_DEFAULT = {"peek": "ignore", "sample": "ignore", "wave": "wrap", "lookup": "clamp"}   # Gen refpages
CMP = {"<", ">", "<=", ">=", "==", "!=", "&&", "||", "^^"}
SIZE_RANGE = (0.0, 4294967296.0)   # dim() / channels(): a count, so x % dim(buf) stays finite (fmod, probes R481, R650)


class FlowError(Exception):
    pass


# ----------------------------------------------------------------- expression tree

class N:
    __slots__ = ("k", "v", "a", "b", "c", "args", "named", "obj", "line", "reach", "bound")

    def __init__(self, k, v=None, a=None, b=None, c=None, line=0):
        self.k, self.v, self.a, self.b, self.c, self.line = k, v, a, b, c, line
        self.args, self.named, self.obj, self.reach = [], {}, None, frozenset()
        self.bound = None        # buffer reads: (boundmode, True if it is the default)

    def children(self):
        if self.k in ("un",):
            return [self.a]
        if self.k == "bin":
            return [self.a, self.b]
        if self.k == "tern":
            return [self.a, self.b, self.c]
        if self.k == "call":
            return self.args + list(self.named.values())
        return []


PREC = {"||": 1, "^^": 1, "&&": 2, "|": 3, "^": 4, "&": 5, "==": 6, "!=": 6, "<": 7, ">": 7, "<=": 7, ">=": 7,
        "<<": 8, ">>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10}


def parse(toks):
    p = _P(toks)
    n = p.ternary()
    if p.i != len(toks):
        raise FlowError("unexpected %r" % toks[p.i].text)
    return n


class _P:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self, k=0):
        j = self.i + k
        return self.t[j].text if j < len(self.t) else None

    def take(self, want=None):
        if self.i >= len(self.t):
            raise FlowError("unexpected end")
        tok = self.t[self.i]
        if want is not None and tok.text != want:
            raise FlowError("expected %r" % want)
        self.i += 1
        return tok

    def ternary(self):
        c = self.binary(1)
        if self.peek() == "?":
            self.take()
            a = self.ternary()
            self.take(":")
            b = self.ternary()
            return N("tern", a=c, b=a, c=b, line=getattr(c, "line", 0))
        return c

    def binary(self, minp):
        left = self.unary()
        while self.peek() in PREC and PREC[self.peek()] >= minp:
            op = self.take().text
            right = self.binary(PREC[op] + 1)
            left = N("bin", op, left, right, line=left.line)
        return left

    def unary(self):
        if self.peek() in ("-", "+", "!", "~"):
            tok = self.take()
            return N("un", tok.text, self.unary(), line=tok.line)
        return self.primary()

    def primary(self):
        tok = self.take()
        if tok.kind == "num":
            t = tok.text
            try:
                v = float(int(t, 16)) if t[:2] in ("0x", "0X") else float(t)
            except OverflowError:
                v = INF                       # a hex literal too big for a double
            return N("num", v, line=tok.line)
        if tok.kind == "str":
            return N("str", tok.text, line=tok.line)
        if tok.text == "(":
            n = self.ternary()
            self.take(")")
            return n
        if tok.kind == "id":
            if self.peek() == "(":
                return self.call(tok.text, None, tok.line)
            if self.peek() == "." and self.peek(2) == "(":
                self.take(".")
                m = self.take()
                return self.call(m.text, tok.text, tok.line)
            return N("var", tok.text, line=tok.line)
        raise FlowError("unexpected %r" % tok.text)

    def call(self, name, obj, line):
        n = N("call", name, line=line)
        n.obj = obj
        self.take("(")
        while self.peek() != ")":
            if self.t[self.i].kind == "id" and self.peek(1) == "=":
                key = self.take().text
                self.take("=")
                n.named[key] = self.ternary()
            else:
                n.args.append(self.ternary())
            if self.peek() == ",":
                self.take()
        self.take(")")
        if obj is not None:
            n.args.insert(0, N("var", obj, line=line))  # the object is read too
            n.v = name
            return n
        return operator_form(n)


CALL_OPS = {"add": "+", "sub": "-", "mul": "*", "div": "/", "mod": "%"}
CALL_ROPS = {"rsub": "-", "rdiv": "/", "rmod": "%"}


def operator_form(n):
    """the function forms of operators as operators: switch(c, a, b) is c ? a : b, div(a, b) is a / b (div(x, 0)
    gives 0 like x / 0, probes R663, R482), mod(a, b) is a % b (probe R664). A user function of one of these names
    is ignored by Max: the operator runs (probes R622, R820)"""
    a = n.args
    if n.named:
        return n
    if n.v == "switch" and len(a) == 3:
        return N("tern", a=a[0], b=a[1], c=a[2], line=n.line)
    if n.v in CALL_OPS and len(a) == 2:
        return N("bin", CALL_OPS[n.v], a[0], a[1], line=n.line)
    if n.v in CALL_ROPS and len(a) == 2:
        return N("bin", CALL_ROPS[n.v], a[1], a[0], line=n.line)
    if n.v == "neg" and len(a) == 1:
        return N("un", "-", a[0], line=n.line)
    return n


# ----------------------------------------------------------------- intervals

def _fix(lo, hi):
    if lo != lo or hi != hi:
        return None
    return (lo, hi)


def i_add(a, b):
    if a is None or b is None:
        return None
    return _fix(a[0] + b[0], a[1] + b[1])


def i_neg(a):
    return None if a is None else (-a[1], -a[0])


def i_sub(a, b):
    return i_add(a, i_neg(b))


def i_mul(a, b):
    if a is None or b is None:
        return None
    if a == ZERO or b == ZERO:
        return ZERO
    ps = []
    for x in a:
        for y in b:
            if (x == 0 and abs(y) == INF) or (y == 0 and abs(x) == INF):
                ps.append(0.0)
            else:
                ps.append(x * y)
    return _fix(min(ps), max(ps))


def i_div(a, b):
    """x / 0 is 0 in Max (probes R482, R483, R663), but a divisor near 0 still gives huge values"""
    if a is None or b is None:
        return None
    if b == ZERO:
        return ZERO
    if b[0] > 0 or b[1] < 0:
        return i_mul(a, (1 / b[1], 1 / b[0]))
    up = i_mul(a, (1 / b[1], INF)) if b[1] > 0 else ZERO
    down = i_mul(a, (-INF, 1 / b[0])) if b[0] < 0 else ZERO
    return i_hull(ZERO, i_hull(up, down))


EMPTY = object()     # an empty interval: the branch of ?: that cannot run


def i_meet(a, b):
    """intersection of two intervals (EMPTY if they do not meet)"""
    if a is None:
        return b
    if b is None:
        return a
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return (lo, hi) if lo <= hi else EMPTY


def i_hull(a, b):
    if a is None or b is None:
        return None
    return (min(a[0], b[0]), max(a[1], b[1]))


def i_absmax(a):
    return INF if a is None else max(abs(a[0]), abs(a[1]))


def finite(a):
    return a is not None and abs(a[0]) != INF and abs(a[1]) != INF


def mono(f, a):
    if a is None:
        return None
    try:
        x, y = f(a[0]), f(a[1])
    except (OverflowError, ValueError, ZeroDivisionError):
        return None
    return _fix(min(x, y), max(x, y))


def _exp(x):
    try:
        return math.exp(x)
    except OverflowError:
        return INF


def _pow(x, y):
    """x ** y for finite x >= 0, y >= 0, as floats (never Python's exact int power); overflow -> inf"""
    try:
        return float(x) ** float(y)
    except OverflowError:
        return INF


# ----------------------------------------------------------------- flow

class Def:
    # in_loop: None outside loops; inside, how many times the enclosing loops run it per sample (a product of
    # constant for-loop counts), or 0 when that is not known
    __slots__ = ("name", "rhs", "line", "in_loop")

    def __init__(self, name, rhs, line, in_loop):
        self.name, self.rhs, self.line, self.in_loop = name, rhs, line, in_loop


SKIP = object()      # coef_item: the value of an earlier loop round, not known yet (left out of the hull)
MAX_ROUNDS = 64


class Flow:
    def __init__(self, items, decls, ref=None, funcs=None):
        self.decls = decls                     # name -> (kind, line, args, named)
        self.funcs = funcs or {}               # user functions Max runs (not ones named like an operator)
        self.fstack = []
        self.defs, self.def_ids = [], {}
        self.reads_checked = []                # (call node, index node, interp mode, which argument)
        self.notes = []                        # (line, msg) for statements the flow model could not read
        self.hist = [n for n, d in decls.items() if d[0] == "History"]
        self.params = {}
        for n, d in decls.items():
            if d[0] == "Param":
                self.params[n] = d
        env = {h: frozenset([("S", h)]) for h in self.hist}
        self.resolving, self.gen_memo = True, {}
        self.carry, self.carried, self.round_budget = {}, set(), 5000
        env = self.walk([n for n in items if n.kind != "func"], env, None)
        self.update = {h: env.get(h, frozenset()) for h in self.hist}
        self.memo_ival, self.memo_deps, self.memo_coef, self.memo_unb = {}, {}, {}, {}
        self.busy = set()
        self.fixed = {}                        # name -> point interval while fixed_stable() tries one setting
        self.hist_ival = self.history_ranges()
        self.memo_ival = {}
        self.unsafe = self.loop_gains()

    def history_ranges(self, rounds=16):
        """value range of every History: start from the declared value, apply the update until nothing
        grows (values that keep growing after `rounds` steps are left unknown)"""
        init = {}
        for h in self.hist:
            d = self.decls[h][2]
            try:
                v = float(d[0].text().replace(" ", "")) if d else 0.0
                init[h] = (v, v)
            except ValueError:
                init[h] = None
        cur = dict(init)
        self.hist_ival = cur
        for _ in range(rounds):
            self.memo_ival = {}
            new = {}
            for h in self.hist:
                v = cur[h]
                for it in self.update[h]:
                    if isinstance(it, tuple):
                        continue
                    v = i_hull(v, self.ival_item(it))
                new[h] = v
            if new == cur:
                return cur
            prev, cur = cur, new
            self.hist_ival = cur
        # still moving: open the bounds that move, apply the update once, and keep the result if it holds (one more
        # step stays inside it). A cap like 'a = a < 1 ? a * 1.01 : 1' is found this way
        wide = {h: None if cur[h] is None or prev[h] is None else
                (cur[h][0] if cur[h][0] == prev[h][0] else -INF, cur[h][1] if cur[h][1] == prev[h][1] else INF)
                for h in self.hist}
        narrow = self.range_step(wide, init)
        if narrow != wide and self.range_step(narrow, init) == narrow:
            return narrow
        self.memo_ival = {}
        last = cur
        for h in self.hist:                 # one more step: whatever still moves is unknown
            v = cur[h]
            for it in self.update[h]:
                if not isinstance(it, tuple):
                    v = i_hull(v, self.ival_item(it))
            if v != last[h]:
                cur = dict(cur)
                cur[h] = None
        return cur

    def range_step(self, cur, init):
        """History ranges after one more update from ranges cur (joined with the start values); None where unknown"""
        self.hist_ival, self.memo_ival = cur, {}
        new = {}
        for h in self.hist:
            v = init[h]
            for it in self.update[h]:
                v = i_hull(v, cur[h] if isinstance(it, tuple) else self.ival_item(it))
            new[h] = v if finite(v) else None
        self.memo_ival = {}
        return new

    # ---- walk statements in order
    def ast(self, node, attr, toks):
        cache = "_ast_" + attr
        if not hasattr(node, cache):
            try:
                setattr(node, cache, parse(toks))
            except FlowError as e:
                setattr(node, cache, None)
                self.notes.append((node.line, str(e)))
        return getattr(node, cache)

    def resolve(self, n, env):
        if n is None or not self.resolving:
            return
        if n.k == "var":
            n.reach = n.reach | env.get(n.v, frozenset())
            return
        if n.k == "call":
            mode = None
            if n.obj is None and n.v in self.funcs and n.v not in self.fstack:
                self.call_into(n, env)
            if n.v in INTERP_DEFAULT:
                it = n.named.get("interp")
                mode = it.v.strip("\"'") if it is not None and it.k == "str" else INTERP_DEFAULT[n.v]
                # wave(buf, phase, start, end): start and end are sample positions too (refpage gen_dsp_wave); with
                # three arguments the third may be the channel offset, so only four or more are read that way
                parts = [(1, "index")] + ([(2, "start position"), (3, "end position")] if n.v == "wave" and
                                          len(n.args) >= 4 else [])
                for pos, part in parts:
                    idx = n.args[pos] if len(n.args) > pos else None
                    if mode not in ("none", "step") and idx is not None:
                        if not any(r[0] is n and r[1] is idx for r in self.reads_checked):
                            self.reads_checked.append((n, idx, mode, part))
                bm = n.named.get("boundmode")
                n.bound = (bm.v.strip("\"'"), False) if bm is not None and bm.k == "str" else (BOUND_DEFAULT[n.v], True)
        for c in n.children():
            self.resolve(c, env)

    def call_into(self, n, env):
        """walk the body of the user function called at n, its parameters bound to the call's arguments (Max inlines
        user functions), so buffer reads inside it are checked too. Every call site adds to the same body"""
        f = self.funcs[n.v]
        penv = {}
        for pos, p in enumerate(f.params):
            if pos < len(n.args):
                node = n.args[pos]
            elif p in n.named:
                node = n.named[p]
            elif p in f.defaults:
                try:
                    node = parse(f.defaults[p].toks)
                except FlowError:
                    node = N("num", 0.0, line=n.line)
            else:
                node = N("num", 0.0, line=n.line)          # a missing argument is 0 (probe R620)
            key = ("arg", id(n), pos)
            if key not in self.def_ids:
                self.def_ids[key] = len(self.defs)
                self.defs.append(Def(p, node, n.line, None))
            penv[p] = frozenset([self.def_ids[key]])
        self.fstack.append(n.v)
        try:
            self.walk(f.body, penv, None)
        finally:
            self.fstack.pop()

    def walk(self, stmts, env, in_loop):
        for s in stmts:
            env = self.stmt(s, env, in_loop)
        return env

    def items(self, s):
        """the comma-separated values on the right of an assignment (a, b = x, y), parsed once"""
        if not hasattr(s, "_ast_items"):
            out = []
            for part in split_top(s.expr.toks) if s.expr.toks else ():     # 'return;' has no value
                try:
                    out.append(parse(part))
                except FlowError as e:
                    out = None
                    self.notes.append((s.line, str(e)))
                    break
            s._ast_items = out or None
        return s._ast_items

    @staticmethod
    def target_rhs(s, items):
        """value node of each target of 'a, b, c = x, y': names pair with the values in order; only the last
        value spreads (a call with several outputs fills the remaining names, probes R957, R958); after a plain
        value the remaining names get 0 (probe R642). Compound ops (a += x) read the target too"""
        if not hasattr(s, "_rhs"):
            out = []
            for pos, (name, line) in enumerate(s.targets):
                if pos < len(items):
                    rhs = items[pos]
                elif items[-1].k == "call":
                    rhs = items[-1]
                else:
                    rhs = N("num", 0.0, line=line)
                if s.op != "=":
                    rhs = N("bin", s.op[0], N("var", name, line=line), rhs, line=line)
                out.append(rhs)
            s._rhs = out
        return s._rhs

    def stmt(self, s, env, in_loop):
        k = s.kind
        if k == "assign":
            items = self.items(s)
            if items is None:
                return env
            rhss = self.target_rhs(s, items)
            done = set()
            for n in items[len(rhss):] + rhss:      # every value is read before any target changes
                if id(n) not in done:
                    done.add(id(n))
                    self.resolve(n, env)
            env = dict(env)
            for pos, (name, line) in enumerate(s.targets):
                key = (id(s), pos)
                if key not in self.def_ids:
                    self.def_ids[key] = len(self.defs)
                    self.defs.append(Def(name, rhss[pos], line, in_loop))
                env[name] = frozenset([self.def_ids[key]])
            return env
        if k == "return":                     # return a, b; in a function: several values
            for part in self.items(s) or ():
                self.resolve(part, env)
            return env
        if k == "expr":
            self.resolve(self.ast(s, "e", s.expr.toks), env)
            return env
        if k == "decl":
            return env
        if k == "if":
            self.resolve(self.ast(s, "cond", s.cond.toks), env)
            et = self.walk(s.then, dict(env), in_loop)
            ee = self.walk(s.els, dict(env), in_loop) if s.els is not None else env
            return merge(et, ee)
        if k in ("for", "while"):
            init = s.init if k == "for" else []
            env = self.walk(init, env, in_loop)
            rounds = self.loop_rounds(s, in_loop)
            head = merge(env, self.loop_gen(s, rounds))   # values at the loop head: before the loop, or an earlier round
            if not self.resolving:
                return head
            if s.cond is not None:
                self.resolve(self.ast(s, "cond", s.cond.toks), head)
            return merge(head, self.walk(s.body + (s.step if k == "for" else []), dict(head), rounds))
        if k == "block":
            return self.walk(s.body, env, in_loop)
        return env

    def loop_rounds(self, s, outer):
        """how many times the body of loop s runs per sample, counting the enclosing loops (outer), or 0 if unknown"""
        n = loop_count(s)
        if outer == 0 or n is None:
            return 0
        r = (outer or 1) * max(n, 1)
        return r if r <= 1000000 else 0

    def loop_gen(self, s, rounds=0):
        """assignments of loop s that may reach the end of its body (and so the next round), from one walk that only
        follows assignments. Memoized, and an inner loop reuses its own, so nested loops cost linear time (two walks
        per level once made depth 20 take 8 s)"""
        g = self.gen_memo.get(id(s))
        if g is None:
            saved, self.resolving = self.resolving, False
            try:
                g = self.walk(s.body + (s.step if s.kind == "for" else []), {}, rounds)
            finally:
                self.resolving = saved
            self.gen_memo[id(s)] = g
        return g

    # ---- value intervals
    def ival(self, n):
        """interval of n, or None if unknown. Never raises on odd arithmetic (inverted bounds, nan, inf * 0)"""
        try:
            v = self._ival(n)
        except (ArithmeticError, ValueError):
            return None
        if v is None or v[0] != v[0] or v[1] != v[1]:
            return None
        return v if v[0] <= v[1] else (v[1], v[0])

    def _ival(self, n):
        k = n.k
        if k == "num":
            return (n.v, n.v)
        if k == "str":
            return None
        if k == "var":
            name = n.v
            if name in CONSTS:
                return (CONSTS[name], CONSTS[name])
            if name in self.fixed:
                return self.fixed[name]
            if name in RANGES:
                return RANGES[name]
            if re.fullmatch(r"in\d*", name):
                return None
            if name in self.params:
                return self.param_range(name)
            if not n.reach:
                return None
            out = None
            first = True
            for it in n.reach:
                v = self.ival_item(it)
                out = v if first else i_hull(out, v)
                first = False
            return out
        if k == "un":
            if n.v == "-":
                return i_neg(self.ival(n.a))
            if n.v == "!":
                return (0.0, 1.0)
            if n.v == "+":
                return self.ival(n.a)
            return None
        if k == "bin":
            op = n.v
            if op in CMP:
                return (0.0, 1.0)
            fr = frac_form(n)
            if fr is not None:
                return fr
            a, b = self.ival(n.a), self.ival(n.b)
            if op == "+":
                return i_add(a, b)
            if op == "-":
                return i_sub(a, b)
            if op == "*":
                if same_tree(n.a, n.b):         # x * x is never negative
                    if a is None:
                        return (0.0, INF)
                    sq = (a[0] * a[0], a[1] * a[1])
                    return (0.0 if a[0] <= 0 <= a[1] else min(sq), max(sq))
                return i_mul(a, b)
            if op == "/":
                return i_div(a, b)
            if op == "%":                   # fmod: keeps the sign of a (probes R481, R650); x % 0 = 0 (R484)
                m = i_absmax(b)
                if m == INF:
                    return None
                if a is not None and a[0] >= 0:
                    return (0.0, m)
                if a is not None and a[1] <= 0:
                    return (-m, 0.0)
                return (-m, m)
            return None
        if k == "tern":
            r = self.refine(n.a)
            if r is None:
                return i_hull(self.ival(n.b), self.ival(n.c))
            name, cur, when_true, when_false = r
            vals = [self.ival_given(name, i_meet(cur, w), x) for w, x in ((when_true, n.b), (when_false, n.c))]
            vals = [v for v in vals if v is not EMPTY]
            return None if not vals else vals[0] if len(vals) == 1 else i_hull(vals[0], vals[1])
        if k == "call":
            return self.ival_call(n)
        return None

    def refine(self, cond):
        """for a condition 'x < C' (or <=, >, >=, either side): (x, range of x, range of x where it is true, where
        it is false), else None. Used to see that 'x > 100 ? 1 : x * 2' never exceeds 200"""
        if cond is None or cond.k != "bin" or cond.v not in ("<", "<=", ">", ">="):
            return None
        a, b, op = cond.a, cond.b, cond.v
        if a.k != "var" and b.k == "var":
            a, b, op = b, a, {"<": ">", ">": "<", "<=": ">=", ">=": "<="}[op]
        if a.k != "var" or a.v in self.fixed:
            return None
        c, cur = self.ival(b), self.ival(a)
        if c is None or cur is None:
            return None
        below, above = (-INF, c[1]), (c[0], INF)
        return (a.v, cur) + ((below, above) if op in ("<", "<=") else (above, below))

    def ival_given(self, name, rng, n):
        """interval of n while variable name is known to be in rng (EMPTY: that branch never runs)"""
        if rng is EMPTY:
            return EMPTY
        saved = (self.fixed, self.memo_ival)
        self.fixed = dict(self.fixed)
        self.fixed[name] = rng
        self.memo_ival = {}
        try:
            return self.ival(n)
        finally:
            self.fixed, self.memo_ival = saved

    def param_range(self, name):
        _, _, args, named = self.params[name]
        lo, hi = named.get("min"), named.get("max")
        try:
            lo = float(lo.text().replace(" ", "")) if lo is not None else None
            hi = float(hi.text().replace(" ", "")) if hi is not None else None
        except ValueError:
            return None
        if lo is None or hi is None:
            return None
        return (min(lo, hi), max(lo, hi))

    def ival_item(self, it):
        if isinstance(it, tuple):           # History state
            return self.hist_ival.get(it[1]) if hasattr(self, "hist_ival") else None
        key = ("i", it)
        if key in self.memo_ival:
            return self.memo_ival[key]
        if key in self.busy:
            return None
        self.busy.add(key)
        v = self.ival(self.defs[it].rhs)
        self.busy.discard(key)
        self.memo_ival[key] = v
        return v

    def ival_call(self, n):
        f = n.v
        if f in ("dim", "channels") and not n.named:
            return SIZE_RANGE                 # a sample or channel count of a Data / Buffer: finite
        a = [self.ival(x) for x in n.args] if n.obj is None else []
        if n.obj is not None:
            return None
        if f in ("clamp", "clip") and len(a) == 3:
            x, lo, hi = a
            if lo is None or hi is None:
                return None
            # Max 9.2.0: clamp(0.5, 1, 0) = 1 (probe R494), i.e. max(lo, min(x, hi)); nan -> a bound (R656, R841)
            if x is None:
                return (lo[0], max(lo[1], hi[1]))
            return (max(lo[0], min(x[0], hi[0])), max(lo[1], min(x[1], hi[1])))
        if f == "fract" and len(a) == 1 and a[0] is not None and a[0][0] >= 0:
            return (0.0, 1.0)
        if f in POINT_FUNCS and len(a) == 1 and a[0] is not None and a[0][0] == a[0][1] and abs(a[0][0]) != INF:
            try:                            # a fixed argument (constants, samplerate fixed): the exact value
                v = POINT_FUNCS[f](a[0][0])
            except (ValueError, OverflowError):
                return None
            return (v, v)
        if f in ("sin", "cos", "fastsin", "fastcos", "tanh", "noise", "triangle", "cycle", "fract", "sign"):
            return (-1.0, 1.0)
        if f in ("phasor", "train", "step", "smoothstep", "isnan", "isdenorm", "bool", "not", "and", "or", "xor") or f in (
                "gt", "gte", "lt", "lte", "eq", "neq", "gtp", "ltp", "gtep", "ltep", "eqp", "neqp"):
            return (0.0, 1.0)
        if f == "atan":
            return (-math.pi / 2, math.pi / 2)
        if f == "atan2":
            return (-math.pi, math.pi)
        if f in ("wrap", "fold", "phasewrap"):
            if f == "phasewrap":
                return (-math.pi, math.pi)
            if len(a) == 3 and a[1] is not None and a[2] is not None:
                return (min(a[1][0], a[2][0]), max(a[1][1], a[2][1]))
            if len(a) == 1:
                return (0.0, 1.0)
            return None
        if f in ("min", "minimum") and len(a) == 2:
            x, y = a
            if x is None and y is None:
                return None
            if x is None or y is None:
                k = x or y
                return (-INF, k[1])
            return (min(x[0], y[0]), min(x[1], y[1]))
        if f in ("max", "maximum") and len(a) == 2:
            x, y = a
            if x is None and y is None:
                return None
            if x is None or y is None:
                k = x or y
                return (k[0], INF)
            return (max(x[0], y[0]), max(x[1], y[1]))
        if f == "abs" and len(a) == 1:
            x = a[0]
            if x is None:
                return None
            m = max(abs(x[0]), abs(x[1]))
            return (0.0 if x[0] <= 0 <= x[1] else min(abs(x[0]), abs(x[1])), m)
        if f in ("fixnan", "fixdenorm") and len(a) == 1:
            return i_hull(a[0], ZERO) if a[0] is not None else None
        if f in ("floor", "ceil", "round", "trunc", "int") and len(a) == 1:
            if a[0] is None:
                return None
            lo, hi = a[0]
            # floats, not Python ints: a huge int bound in pow() below once took forever (int ** int)
            return (float(math.floor(lo)) if abs(lo) != INF else lo, float(math.ceil(hi)) if abs(hi) != INF else hi)
        # exp-like functions are never negative, also when the argument range is unknown
        if f in ("exp", "fastexp") and len(a) == 1:
            return mono(_exp, a[0]) if a[0] is not None else (0.0, INF)
        if f == "exp2" and len(a) == 1:
            return mono(lambda v: _exp(v * math.log(2)), a[0]) if a[0] is not None else (0.0, INF)
        if f in ("pow", "fastpow") and len(a) == 2:
            x, y = a
            if x is not None and y is not None and x[0] > 0:
                cs = [_exp(yy * math.log(xx)) for xx in x for yy in y]
                return (min(cs), max(cs))
            # pow(0, -1) = 0 and a negative base with a non-integer exponent gives 0 (probes R495, R487, R830)
            if x is not None and y is not None and x[0] >= 0 and y[0] >= 0 and finite(x) and finite(y):
                cs = [_pow(xx, yy) for xx in x for yy in y]   # x >= 0, y >= 0: the corners hold the extremes
                return (min(cs), max(cs))
            if x is not None and x[0] >= 0:
                return (0.0, INF)
            if y is not None and y[0] == y[1] and y[0] % 2 == 0:
                return (0.0, INF)                 # pow(x, 2): even powers (probe R651)
            return None
        if f == "sqrt" and len(a) == 1 and a[0] is not None and a[0][0] >= 0:
            return mono(math.sqrt, a[0])
        if f in ("log", "ln", "log2", "log10") and len(a) == 1 and a[0] is not None and a[0][0] > 0:
            base = {"log": math.e, "ln": math.e, "log2": 2, "log10": 10}[f]
            return mono(lambda v: math.log(v, base) if v != INF else INF, a[0])
        if f == "mix" and len(a) == 3:
            return i_add(a[0], i_mul(i_sub(a[1], a[0]), a[2]))
        if f == "selector" and len(a) >= 2:
            out = ZERO                       # index <= 0 gives 0, above the count the last input (probes R971, R972)
            for v in a[1:]:
                out = i_hull(out, v)
            return out
        if f == "t60" and len(a) == 1 and a[0] is not None and a[0][0] > 0:
            return mono(lambda v: _exp(math.log(0.001) / v), a[0])
        if f == "t60" and len(a) == 1 and a[0] is not None and a[0][0] == 0:
            return (0.0, 1.0)                      # t60(0) = 1 (probe R493), t60(x > 0) is in (0, 1)
        if f == "dbtoa" and len(a) == 1:
            return mono(lambda v: _exp(v / 20 * math.log(10)), a[0]) if a[0] is not None else (0.0, INF)
        if f == "mtof" and len(a) == 1:
            return mono(lambda v: 440 * _exp((v - 69) / 12 * math.log(2)), a[0]) if a[0] is not None else (0.0, INF)
        if f == "mstosamps" and len(a) == 1:
            return i_mul(a[0], (RANGES["samplerate"][0] / 1000, RANGES["samplerate"][1] / 1000))
        if f == "sampstoms" and len(a) == 1:
            return i_mul(a[0], (1000 / RANGES["samplerate"][1], 1000 / RANGES["samplerate"][0]))
        return None

    def mod_cut(self, n):
        """x % m with a finite m stays within m for finite x, so it stops feedback growth like wrap(); it does
        not stop a runaway x (fmod(inf, m) is nan), so unbounded() still follows x"""
        return n.v == "%" and finite(self.ival(n.b))

    # ---- which History values a node depends on (through cuts)
    def deps(self, n):
        k = n.k
        if k in ("num", "str"):
            return frozenset()
        if k == "var":
            out = frozenset()
            for it in n.reach:
                out |= self.deps_item(it)
            return out
        if k == "bin" and (n.v in CMP or self.mod_cut(n) or frac_form(n)):
            return frozenset()
        if k == "un" and n.v == "!":
            return frozenset()
        if k == "tern":
            return self.deps(n.b) | self.deps(n.c)
        if k == "call":
            if n.obj is not None or n.v in BOUNDED_OUT or n.v in WRAPPERS:
                return frozenset()
            if n.v == "selector" and n.args:     # the index only picks an input, like the condition of ?:
                out = frozenset()
                for x in n.args[1:]:
                    out |= self.deps(x)
                return out
            if n.v in ("min", "max", "minimum", "maximum") and len(n.args) == 2 and any(
                    finite(self.ival(x)) for x in n.args):
                return frozenset()
        out = frozenset()
        for c in n.children():
            out |= self.deps(c)
        return out

    def deps_item(self, it):
        if isinstance(it, tuple):
            return frozenset([it[1]])
        key = ("d", it)
        if key in self.memo_deps:
            return self.memo_deps[key]
        if key in self.busy:
            return frozenset()
        self.busy.add(key)
        v = self.deps(self.defs[it].rhs)
        self.busy.discard(key)
        self.memo_deps[key] = v
        return v

    # ---- coefficient of the previous value of History s in a node
    def coef(self, n, s):
        k = n.k
        if k in ("num", "str"):
            return ZERO
        if k == "var":
            out, first = None, True
            for it in n.reach:
                c = self.coef_item(it, s)
                if c is SKIP:
                    continue
                out = c if first else i_hull(out, c)
                first = False
            return ZERO if first else out
        if k == "un":
            if n.v == "!":
                return ZERO
            c = self.coef(n.a, s)
            return i_neg(c) if n.v == "-" else (c if n.v == "+" else (ZERO if c == ZERO else None))
        if k == "bin":
            op = n.v
            if op in CMP or self.mod_cut(n) or frac_form(n):
                return ZERO
            ca, cb = self.coef(n.a, s), self.coef(n.b, s)
            if ca == ZERO and cb == ZERO:
                return ZERO                 # neither side depends on s, whatever their range (x * 0.01)
            if op == "+":
                return i_add(ca, cb)
            if op == "-":
                return i_sub(ca, cb)
            if op == "*":
                if ca == ZERO:
                    return i_mul(cb, self.ival(n.a))
                if cb == ZERO:
                    return i_mul(ca, self.ival(n.b))
                return None
            if op == "/":
                if cb == ZERO:
                    return i_div(ca, self.ival(n.b)) if ca != ZERO else ZERO
                return None
            return ZERO if (ca == ZERO and cb == ZERO) else None
        if k == "tern":
            return i_hull(self.coef(n.b, s), self.coef(n.c, s))
        if k == "call":
            f = n.v
            if n.obj is not None or f in BOUNDED_OUT or f in WRAPPERS:
                return ZERO
            if f == "selector" and n.args:     # 0 or one of the inputs (probes R971, R972)
                out = ZERO
                for x in n.args[1:]:
                    out = i_hull(out, self.coef(x, s))
                return out
            cs = [self.coef(x, s) for x in n.args]
            if all(c == ZERO for c in cs):
                return ZERO
            if f in ("min", "max", "minimum", "maximum") and len(n.args) == 2:
                if any(finite(self.ival(x)) for x in n.args):
                    return ZERO            # one side is a finite cap
                return i_hull(cs[0], cs[1])
            if f in MAG_KEEP and len(cs) >= 1:
                m = i_absmax(cs[0])
                return None if m == INF else (-m, m)
            if f == "mix" and len(n.args) == 3 and cs[2] == ZERO:
                t = self.ival(n.args[2])
                return i_add(i_mul(cs[0], i_sub(ONE, t)), i_mul(cs[1], t))
            return None
        return None

    def coef_item(self, it, s):
        if isinstance(it, tuple):
            return ONE if it[1] == s else ZERO
        if s not in self.deps_item(it):
            return ZERO
        key = ("c", it, s)
        if key in self.memo_coef:
            return self.memo_coef[key]
        if key in self.busy:                # loop-carried inside one sample: the value of the round before
            self.carried.add(key)
            return self.carry.get(key, SKIP)
        self.busy.add(key)
        before = set(self.memo_coef)
        v = self.coef(self.defs[it].rhs, s)
        if key in self.carried:
            v = self.loop_coef(it, key, s, v, before)
        self.busy.discard(key)
        self.memo_coef[key] = v
        return v

    def loop_coef(self, it, key, s, v, before):
        """coefficient of a definition that reads its own value from the round before (acc += h * fb in a loop):
        repeat it for the number of rounds of a constant for loop (4 x 0.5 is 2, 4 x 1.2 is 2.07). More than
        MAX_ROUNDS rounds, a loop whose rounds are not known, or too much work: unknown"""
        n = self.defs[it].in_loop or 0
        cur = total = v if 0 < n <= MAX_ROUNDS else None    # rounds not known (while, other for forms): unknown
        for _ in range(1, n if total is not None else 1):
            self.round_budget -= 1
            if cur is None or self.round_budget < 0:
                total = None                 # nested loop-carried values: give up rather than take minutes
                break
            self.carry[key] = cur
            for k in set(self.memo_coef) - before:   # values computed with the round before: stale now
                del self.memo_coef[k]
            cur = self.coef(self.defs[it].rhs, s)
            total = i_hull(total, cur)
        self.carry.pop(key, None)
        self.carried.discard(key)
        for k in set(self.memo_coef) - before:
            del self.memo_coef[k]
        return total

    # ---- feedback groups and their loop gain
    def loop_gains(self):
        graph = {}
        for h in self.hist:
            d = frozenset()
            for it in self.update[h]:
                d |= self.deps_item(it)
            graph[h] = d & set(self.hist)
        unsafe = {}
        for comp in sccs(graph):
            cyclic = len(comp) > 1 or any(h in graph[h] for h in comp)
            if not cyclic:
                continue
            worst = None
            for h in comp:
                for it in self.update[h]:
                    rs = 0.0
                    for s in comp:
                        rs += i_absmax(self.coef_item(it, s))
                    if rs > 1 + 1e-9 and (worst is None or rs > worst[1]):
                        worst = (h, rs)
            if worst and all(finite(self.hist_ival.get(h)) for h in comp):
                continue                     # every value of the group stays in a finite range (history_ranges)
            if worst and not self.fixed_stable(comp):
                for h in comp:
                    unsafe[h] = worst
        return unsafe

    def fixed_stable(self, comp, max_inputs=4):
        """True for a feedback group that is linear in its Histories, with coefficients that depend only on
        constants, Params and samplerate (a biquad or state-variable filter with fixed settings), when for every
        setting tried (each such input at its min, middle and max) the coefficient matrix has spectral radius < 1.
        The row-sum test above can exceed 1 for such a stable filter. A filter whose settings move fast, or that is
        unstable between the settings tried, is not caught"""
        if len(comp) > 8:
            return False                     # keep it cheap: filters have a few states
        items = []
        for h in comp:
            ups = list(self.update[h])
            if len(ups) != 1 or isinstance(ups[0], tuple):
                return False                 # a History that keeps its value on some path: not a fixed matrix
            items.append(ups[0])
        slow = self.slow_inputs(items)
        if slow is None or len(slow) > max_inputs:
            return False
        grids = []
        for name in sorted(slow):
            r = RANGES.get(name) if name in RANGES else self.param_range(name)
            if r is None or not finite(r):
                return False
            grids.append([(name, (v, v)) for v in sorted({r[0], (r[0] + r[1]) / 2, r[1]})])
        saved = (self.memo_ival, self.memo_coef, self.fixed)
        try:
            for combo in itertools.product(*grids):
                self.fixed = dict(combo)
                self.memo_ival, self.memo_coef = {}, {}
                m = []
                for it in items:
                    row = []
                    for s in comp:
                        c = self.coef_item(it, s)
                        if not finite(c) or c[1] - c[0] > 1e-9 * max(1.0, abs(c[0])):
                            return False     # depends on a signal or on state: not a fixed coefficient
                        row.append((c[0] + c[1]) / 2)
                    m.append(row)
                if not bounded_matrix(m):
                    return False
            return True
        finally:
            self.memo_ival, self.memo_coef, self.fixed = saved

    def slow_inputs(self, items, limit=5000):
        """Params and samplerate-like names the updates read (through plain variables, not through History)"""
        names, seen, todo = set(), set(), list(items)
        while todo:
            it = todo.pop()
            if it in seen:
                continue
            seen.add(it)
            if len(seen) > limit:
                return None
            stack = [self.defs[it].rhs]
            while stack:
                n = stack.pop()
                if n.k == "var":
                    if n.v in self.params or n.v in RANGES:
                        names.add(n.v)
                    todo += [r for r in n.reach if not isinstance(r, tuple)]
                stack += n.children()
        return names

    # ---- can this value become inf?
    def unbounded(self, n, path=()):
        k = n.k
        if k in ("num", "str"):
            return None
        if k == "var":
            name = n.v
            if re.fullmatch(r"in\d*", name):
                return " -> ".join((name,) + tuple(reversed(path)))
            if name in CONSTS or name in RANGES or name in self.params:
                return None
            for it in n.reach:
                r = self.unb_item(it, path + (name,))
                if r:
                    return r
            return None
        if k == "bin" and (n.v in CMP or frac_form(n)):
            return None
        if k == "un" and n.v == "!":
            return None
        if k == "tern":
            return self.unbounded(n.b, path) or self.unbounded(n.c, path)
        if k == "call":
            if n.obj is not None or n.v in BOUNDED_OUT:
                return None
            if n.v == "selector" and n.args:
                for x in n.args[1:]:
                    r = self.unbounded(x, path)
                    if r:
                        return r
                return None
            if n.v == "counter" and n.args:     # counter(incr, reset, max): reset is a trigger, max a limit
                return self.unbounded(n.args[0], path)
            if n.v in ("min", "max", "minimum", "maximum") and len(n.args) == 2 and all(
                    finite(self.ival(x)) or self.unbounded(x, path) is None for x in n.args):
                return None
        for c in n.children():
            r = self.unbounded(c, path)
            if r:
                return r
        return None

    def unb_item(self, it, path):
        if isinstance(it, tuple):
            h = it[1]
            if h in self.unsafe:
                g = self.unsafe[h]
                return "History %s is in a feedback loop that gencheck cannot show to stay bounded (%s)" % (
                    h, "its gain bound is unknown" if g[1] == INF else "gain bound %s" % (
                        "%.3g" % g[1] if g[1] >= 1.01 else "%.6g" % g[1])) + (
                    " -> " + " -> ".join(reversed(path)) if path and path[-1] != h else "")
            key = ("u", it)
            if key in self.memo_unb:
                return self.memo_unb[key]
            if key in self.busy:
                return None
            self.busy.add(key)
            r = None
            for u in self.update.get(h, ()):
                if u == it:
                    continue
                r = self.unb_item(u, path)
                if r:
                    break
            self.busy.discard(key)
            self.memo_unb[key] = r
            return r
        key = ("v", it)
        if key in self.memo_unb:
            return self.memo_unb[key]
        if key in self.busy:
            return None
        self.busy.add(key)
        r = self.unbounded(self.defs[it].rhs, path)
        self.busy.discard(key)
        self.memo_unb[key] = r
        return r

    def interp_findings(self):
        out = []
        for call, idx, mode, part in self.reads_checked:
            r = self.unbounded(idx)
            if r:
                what = (call.obj + "." if call.obj else "") + call.v
                out.append((call.line, what, mode, r, part, call.bound))
        return out


def _num(n):
    """value of a number node (or -number), else None"""
    if n is not None and n.k == "num":
        return n.v
    if n is not None and n.k == "un" and n.v == "-" and n.a.k == "num":
        return -n.a.v
    return None


def _assigns(stmts, name):
    for x in stmts:
        if x.kind == "assign" and any(t == name for t, _ in x.targets):
            return True
        for sub in ("then", "els", "body", "init", "step"):
            if _assigns(getattr(x, sub, None) or [], name):
                return True
    return False


def loop_count(s):
    """rounds of 'for (i = c0; i < c1; i += c2)' with numbers c0, c1, c2 (also <=, >, >=, -=, i = i + c2) when the
    body does not assign i; None if not known (while loops, other forms)"""
    if s.kind != "for" or len(s.init) != 1 or len(s.step) != 1 or s.cond is None:
        return None
    ini, st = s.init[0], s.step[0]
    if ini.kind != "assign" or len(ini.targets) != 1 or ini.op != "=" or st.kind != "assign" or len(st.targets) != 1:
        return None
    i = ini.targets[0][0]
    if st.targets[0][0] != i or _assigns(s.body, i):
        return None
    try:
        c0, cond, step = _num(parse(ini.expr.toks)), parse(s.cond.toks), parse(st.expr.toks)
    except FlowError:
        return None
    if st.op in ("+=", "-="):
        d = _num(step)
        d = None if d is None else (d if st.op == "+=" else -d)
    elif st.op == "=" and step.k == "bin" and step.v in ("+", "-") and step.a.k == "var" and step.a.v == i:
        d = _num(step.b)
        d = None if d is None else (d if step.v == "+" else -d)
    else:
        d = None
    if c0 is None or d is None or d == 0 or cond.k != "bin":
        return None
    op, a, b = cond.v, cond.a, cond.b
    if b.k == "var" and b.v == i and a.k != "var":
        op, a, b = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}.get(op, op), b, a
    c1 = _num(b)
    if a.k != "var" or a.v != i or c1 is None:
        return None
    if (op in ("<", "<=") and d > 0) or (op in (">", ">=") and d < 0):
        span = (c1 - c0) / d
        if not -1e7 < span < 1e7:            # also inf and nan from huge literals
            return None
        n = math.ceil(span) if op in ("<", ">") else math.floor(span) + 1
        return max(0, int(n))
    return None


def bounded_matrix(m):
    """True if x -> m x cannot grow without limit: some power of m has max-row-sum norm < 1 (spectral radius < 1), or m
    itself has norm <= 1 (a hold, a convex crossfade: no power exceeds 1), or m is 2 x 2 with both eigenvalues on or
    inside the unit circle and not a repeated eigenvalue of size 1 (det <= 1, |trace| <= 1 + det; the magic-circle
    oscillator has det = 1). A repeated eigenvalue 1 (a Jordan block) grows, so this is not a radius-only test"""
    if contracts(m):
        return True
    if max(sum(abs(x) for x in row) for row in m) <= 1 + 1e-9:
        return True
    if len(m) == 2:
        (a, b), (c, d) = m
        det, tr = a * d - b * c, a + d
        if abs(det) <= 1 + 1e-9 and abs(tr) <= 1 + det + 1e-9 and tr * tr - 4 * det < -1e-14:
            return True                      # complex pair on or inside the unit circle: a rotation, bounded
    return False


def contracts(m, rounds=24):
    """True if some power m^(2^j), j < rounds, has max-row-sum norm < 1: then the spectral radius of m is < 1"""
    p = m
    for _ in range(rounds):
        norm = max(sum(abs(x) for x in row) for row in p)
        if norm != norm or norm == INF:
            return False
        if norm < 1 - 1e-9:
            return True
        p = [[sum(p[i][k] * p[k][j] for k in range(len(p))) for j in range(len(p))] for i in range(len(p))]
    return False


def split_top(toks):
    """split tokens at the commas outside ( )"""
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
    parts.append(cur)
    return parts


PURE = set(POINT_FUNCS) | {"abs", "floor", "ceil", "trunc", "int", "round", "min", "max", "clamp", "clip", "pow",
                           "exp", "exp2", "log", "log2", "log10", "sqrt", "wrap", "fold", "fract", "mix", "sign"}


def same_tree(a, b):
    """the same expression written twice (x and floor(x) in x - floor(x)); calls only to pure math functions
    (noise() twice is two different values)"""
    if a.k != b.k or a.v != b.v or a.obj != b.obj or len(a.args) != len(b.args) or set(a.named) != set(b.named):
        return False
    if a.k == "call" and (a.obj is not None or a.v not in PURE):
        return False
    ca, cb = a.children(), b.children()
    return len(ca) == len(cb) and all(same_tree(x, y) for x, y in zip(ca, cb))


# x - f(x): the fractional part, bounded for every finite x (inf gives nan, like fract)
FRAC_FORMS = {"floor": (0.0, 1.0), "trunc": (-1.0, 1.0), "int": (-1.0, 1.0), "ceil": (-1.0, 0.0),
              "round": (-0.5, 0.5)}


def frac_form(n):
    """interval of n if n is x - floor(x) (or trunc, int, ceil, round of the same x), else None"""
    if n.k != "bin" or n.v != "-":
        return None
    b = n.b
    if b.k == "call" and b.obj is None and b.v in FRAC_FORMS and len(b.args) == 1 and not b.named \
            and same_tree(n.a, b.args[0]):
        return FRAC_FORMS[b.v]
    return None


def merge(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, frozenset()) | v
    return out


def sccs(graph):
    """Tarjan, iterative"""
    index, low, on, stack, out = {}, {}, set(), [], []
    counter = [0]
    for root in graph:
        if root in index:
            continue
        work = [(root, iter(graph[root]))]
        index[root] = low[root] = counter[0]
        counter[0] += 1
        stack.append(root)
        on.add(root)
        while work:
            v, it = work[-1]
            nxt = next(it, None)
            if nxt is not None:
                if nxt not in graph:
                    continue
                if nxt not in index:
                    index[nxt] = low[nxt] = counter[0]
                    counter[0] += 1
                    stack.append(nxt)
                    on.add(nxt)
                    work.append((nxt, iter(graph[nxt])))
                elif nxt in on:
                    low[v] = min(low[v], index[nxt])
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[v])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                out.append(comp)
    return out
