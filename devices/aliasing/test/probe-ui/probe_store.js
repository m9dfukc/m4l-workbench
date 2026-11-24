// probe_store.js: blob-storage half of the ProbeUI test device (check G-UI5, see README.md).
// Hand-written for v8 (ES2020, runs in Max 9.1.5 and 9.2); not part of the TS build.
//
// Arguments: buffer~ name, dict name (both ---names, substituted in the box text).
// Inlet 0:  scramble | verify | init | bufname <name> | dictname <name>
// Inlet 1:  output of the two Blob parameters: list from pattr "Probe Table",
//           dictionary from dict "Probe Table Dict"
// Outlet 0: list of 5120 floats -> pattr probetable   (variant A: Blob, Stored Only)
// Outlet 1: dictionary <name>   -> dict ---probedict  (variant B: Blob, Stored Only; it clones it)
// Outlet 2: set <text>          -> status comment on the device face
//
// Both objects echo what they receive; the first message after a store is checked as that echo,
// anything else on inlet 1 is a restore (Live recalls the Set) and is written into the buffer~
// (list preferred, dict if no list arrived). If the dict does not output on recall, init reads it
// by name.

autowatch = 1;
inlets = 2;
outlets = 3;

const CH = 5;
const FRAMES = 1024;
const N = CH * FRAMES;
const TAG = "ProbeUI store";

let bufName = jsarguments.length > 1 ? String(jsarguments[1]) : "";
let dictName = jsarguments.length > 2 ? String(jsarguments[2]) : "";
let lastStored = null; // checksum of the last scramble (this session)
let expectListEcho = false;
let expectDictEcho = false;
let restoredList = null; // values recalled by Live
let restoredDict = null; // {table, sum, wsum, first} recalled by Live
let pendingList = null; // restore that arrived before the buffer~ was reachable
const storeDict = new Dict(); // unnamed scratch dict: Max gives it a unique name

function say(text) {
	post(`${TAG}: ${text}\n`);
	// also as an error line, so it lands in Live's Log.txt ("Message from Max") [open: whether post() does]
	error(`[ProbeUI info, not an error] ${text}\n`);
}
say.local = 1;

function status(text) {
	outlet(2, "set", text);
}
status.local = 1;

function checksum(vals) {
	let sum = 0;
	let wsum = 0;
	for (let i = 0; i < vals.length; i++) {
		sum += vals[i];
		wsum += vals[i] * ((i % 97) + 1);
	}
	return { n: vals.length, sum, wsum, first: vals.slice(0, 3) };
}
checksum.local = 1;

function fmt(c) {
	return `n=${c.n} sum=${c.sum.toPrecision(10)} wsum=${c.wsum.toPrecision(10)} first=${c.first
		.map((v) => Number(v).toPrecision(7))
		.join(",")}`;
}
fmt.local = 1;

function getBuffer() {
	if (!bufName) return null;
	const b = new Buffer(bufName);
	if (b.framecount() < FRAMES || b.channelcount() < CH) return null;
	return b;
}
getBuffer.local = 1;

function readBuffer(b) {
	const vals = [];
	for (let ch = 1; ch <= CH; ch++) {
		const row = b.peek(ch, 0, FRAMES);
		const arr = Array.isArray(row) ? row : [row];
		for (let i = 0; i < FRAMES; i++) vals.push(Number(arr[i]) || 0);
	}
	return vals;
}
readBuffer.local = 1;

function writeBuffer(b, vals) {
	for (let ch = 0; ch < CH; ch++) b.poke(ch + 1, 0, vals.slice(ch * FRAMES, (ch + 1) * FRAMES));
}
writeBuffer.local = 1;

function applyRestore(vals, from) {
	const b = getBuffer();
	if (!b) {
		pendingList = vals;
		say(`RESTORE ${from} held back: buffer~ '${bufName}' not reachable yet (applied on init)`);
		return;
	}
	if (vals.length !== N) {
		say(`RESTORE ${from} not written to the buffer: ${vals.length} values`);
		return;
	}
	writeBuffer(b, vals);
	pendingList = null;
	const c = checksum(readBuffer(b));
	say(`RESTORE ${from} -> buffer ${fmt(c)}`);
	status(`restored (${from}) ${fmt(c)}`);
}
applyRestore.local = 1;

function compareRestores() {
	if (!restoredList || !restoredDict) return;
	const t = restoredDict.table;
	if (restoredList.length !== t.length) {
		say(`COMPARE list n=${restoredList.length} vs dict n=${t.length}: lengths differ`);
		return;
	}
	let maxdiff = 0;
	for (let i = 0; i < t.length; i++) maxdiff = Math.max(maxdiff, Math.abs(restoredList[i] - t[i]));
	const ref = restoredDict.sum;
	const d = typeof ref === "number" ? (checksum(restoredList).sum - ref).toExponential(2) : "n/a";
	say(`COMPARE list vs dict: max|diff|=${maxdiff.toExponential(2)}, list sum - stored sum = ${d}`);
}
compareRestores.local = 1;

// --- messages on inlet 0 ---------------------------------------------------------------------

function bufname(name) {
	bufName = String(name);
}

function dictname(name) {
	dictName = String(name);
}

function scramble() {
	const b = getBuffer();
	if (!b) {
		say(`scramble: buffer~ '${bufName}' not reachable`);
		return;
	}
	const vals = new Array(N);
	for (let i = 0; i < N; i++) vals[i] = Math.random() * 2 - 1;
	writeBuffer(b, vals);
	const stored = readBuffer(b); // float32 as the buffer~ holds them
	lastStored = checksum(stored);
	say(`STORE ${fmt(lastStored)}`);
	status(`stored ${fmt(lastStored)}`);
	expectListEcho = true;
	outlet(0, stored);
	storeDict.parse(
		JSON.stringify({ table: stored, sum: lastStored.sum, wsum: lastStored.wsum, first: lastStored.first }),
	);
	expectDictEcho = true;
	outlet(1, "dictionary", storeDict.name);
}

function verify() {
	const b = getBuffer();
	if (!b) {
		say(`verify: buffer~ '${bufName}' not reachable`);
		return;
	}
	const c = checksum(readBuffer(b));
	say(`BUFFER now ${fmt(c)}`);
	status(`buffer ${fmt(c)}`);
}

function init() {
	if (!restoredDict && dictName) readDict(dictName, "dict (read by name at init)");
	if (pendingList) applyRestore(pendingList, "pending");
	const b = getBuffer();
	const where = b ? `${b.channelcount()}ch x ${b.framecount()}` : "not reachable";
	say(
		`INIT max=${max.version} buffer='${bufName}' (${where}) list restored: ${restoredList ? "yes" : "no"}, ` +
			`dict restored: ${restoredDict ? "yes" : "no"}`,
	);
	if (!restoredList && !restoredDict) status("no stored table yet: press Scramble, save, reopen");
}

// --- pattr output on inlet 1 -----------------------------------------------------------------

function list(...args) {
	if (inlet !== 1) {
		say(`unexpected list of ${args.length} on inlet ${inlet}`);
		return;
	}
	const vals = args.map(Number);
	if (expectListEcho) {
		expectListEcho = false;
		const c = checksum(vals);
		const same = lastStored && c.n === lastStored.n && c.sum === lastStored.sum;
		say(`ECHO list from pattr ${fmt(c)} ${same ? "(identical)" : "(DIFFERS from STORE)"}`);
		return;
	}
	if (vals.length !== N) say(`RESTORE list has ${vals.length} values, expected ${N}`);
	restoredList = vals;
	applyRestore(vals, "list");
	compareRestores();
}

function readDict(name, from) {
	let obj = null;
	try {
		obj = JSON.parse(new Dict(String(name)).stringify());
	} catch (e) {
		say(`dictionary '${name}' unreadable: ${e}`);
		return;
	}
	if (!obj || !Array.isArray(obj.table)) {
		if (!from.startsWith("dict (read")) say(`dictionary '${name}' has no table`);
		return;
	}
	const table = obj.table.map(Number);
	const c = checksum(table);
	if (expectDictEcho) {
		expectDictEcho = false;
		const same = lastStored && c.n === lastStored.n && c.sum === lastStored.sum;
		say(`ECHO dict ${fmt(c)} ${same ? "(identical)" : "(DIFFERS from STORE)"}`);
		return;
	}
	restoredDict = { table, sum: obj.sum, wsum: obj.wsum, first: obj.first };
	const ref = typeof obj.sum === "number" ? obj.sum.toPrecision(10) : "missing";
	say(`RESTORE ${from} ${fmt(c)} (sum stored at save time: ${ref})`);
	if (!restoredList) applyRestore(table, from);
	compareRestores();
}
readDict.local = 1;

function dictionary(name) {
	if (inlet !== 1) {
		say(`unexpected dictionary on inlet ${inlet}`);
		return;
	}
	readDict(name, "dict");
}

function anything() {
	say(`unknown message '${messagename}' on inlet ${inlet}`);
}
