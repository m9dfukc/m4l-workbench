// Host test harness for the aliasing gen~ C++ export (devices/aliasing/gen/aliasing.genexpr).
//
// Compiled by devices/aliasing/test/host/run.sh against the export in build/aliasing/export/cpp
// (tools/gen-export.sh aliasing). Renders the gen~ offline into a float32 stereo WAV; no audio
// device is touched. The exported C++ stays in build/ (gitignored, export licence unchecked).
//
// The table buffers: Max 9.2.1 exports a GenExpr `Buffer x("name")` without a State member; the
// generated code uses an undeclared `x` (dim, channels, read, write). This harness provides
// `atab` and `aheads` as namespace-level float32 buffers before including the export, which is
// also what a bound buffer~ is (32-bit floats).
//
// Usage: render OUT.wav [options]
//   --sr HZ            sample rate (default 48000)
//   --vs N             vector size (default 64)
//   --seconds S        length (default 4)
//   --set NAME=V       set a gen Param at t = 0 (repeatable)
//   --at T NAME=V      set a gen Param at time T seconds (block boundary; repeatable)
//   --gate T0:T1       in1 (MIDI gate) = 1 from T0 to T1 seconds (repeatable)
//   --sync T           one-sample impulse on in2 at T seconds (repeatable)
//   --table OUT.f32    dump the 5 x 1024 table (voice-major float32) at the end
//   --heads OUT.f32    dump the 5 x 3 head buffer (voice-major float32) at the end
//   --params           list the gen Params and exit

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "genlib.h"

struct HostBuffer {
	int dim;
	int channels;
	std::vector<float> data;  // frame-major, interleaved like a buffer~
	HostBuffer(int d, int c) : dim(d), channels(c), data(size_t(d) * size_t(c), 0.f) {}
	t_sample read(long i, long c) const { return data[size_t(i) * channels + c]; }
	void write(t_sample v, long i, long c) { data[size_t(i) * channels + c] = float(v); }
};

namespace aliasing {
HostBuffer atab(1024, 5);
HostBuffer aheads(5, 3);
}  // namespace aliasing

#include "aliasing.cpp"

namespace {

struct ParamChange {
	long frame;
	long index;
	double value;
};

[[noreturn]] void die(const std::string &msg) {
	std::fprintf(stderr, "render: %s\n", msg.c_str());
	std::exit(2);
}

long param_index(CommonState *s, const std::string &name) {
	for (long i = 0; i < aliasing::num_params(); ++i)
		if (name == aliasing::getparametername(s, i)) return i;
	die("unknown param '" + name + "' (use --params)");
}

void parse_assign(CommonState *s, const std::string &a, long frame, std::vector<ParamChange> &out) {
	auto eq = a.find('=');
	if (eq == std::string::npos) die("expected NAME=VALUE, got '" + a + "'");
	out.push_back({frame, param_index(s, a.substr(0, eq)), std::atof(a.c_str() + eq + 1)});
}

void put_u32(FILE *f, uint32_t v) { std::fwrite(&v, 4, 1, f); }
void put_u16(FILE *f, uint16_t v) { std::fwrite(&v, 2, 1, f); }

void write_wav(const char *path, const std::vector<float> &inter, int sr) {
	FILE *f = std::fopen(path, "wb");
	if (!f) die(std::string("cannot write ") + path);
	uint32_t bytes = uint32_t(inter.size() * 4);
	std::fwrite("RIFF", 1, 4, f); put_u32(f, 36 + bytes); std::fwrite("WAVE", 1, 4, f);
	std::fwrite("fmt ", 1, 4, f); put_u32(f, 16); put_u16(f, 3); put_u16(f, 2);
	put_u32(f, uint32_t(sr)); put_u32(f, uint32_t(sr) * 8); put_u16(f, 8); put_u16(f, 32);
	std::fwrite("data", 1, 4, f); put_u32(f, bytes);
	std::fwrite(inter.data(), 4, inter.size(), f);
	std::fclose(f);
}

void dump(const char *path, const HostBuffer &b) {
	FILE *f = std::fopen(path, "wb");
	if (!f) die(std::string("cannot write ") + path);
	for (int c = 0; c < b.channels; ++c)
		for (int i = 0; i < b.dim; ++i) {
			float v = b.data[size_t(i) * b.channels + c];
			std::fwrite(&v, 4, 1, f);
		}
	std::fclose(f);
}

}  // namespace

int main(int argc, char **argv) {
	int sr = 48000, vs = 64;
	double seconds = 4.0;
	const char *out = nullptr, *table = nullptr, *heads = nullptr;
	std::vector<std::string> sets;
	std::vector<std::pair<double, std::string>> ats;
	std::vector<std::pair<double, double>> gates;
	std::vector<double> syncs;
	bool list = false;

	for (int i = 1; i < argc; ++i) {
		std::string a = argv[i];
		auto next = [&]() -> const char * { if (++i >= argc) die("missing value after " + a); return argv[i]; };
		if (a == "--sr") sr = std::atoi(next());
		else if (a == "--vs") vs = std::atoi(next());
		else if (a == "--seconds") seconds = std::atof(next());
		else if (a == "--set") sets.push_back(next());
		else if (a == "--at") { double t = std::atof(next()); ats.push_back({t, next()}); }
		else if (a == "--gate") {
			std::string g = next(); auto c = g.find(':');
			if (c == std::string::npos) die("--gate T0:T1");
			gates.push_back({std::atof(g.c_str()), std::atof(g.c_str() + c + 1)});
		}
		else if (a == "--sync") syncs.push_back(std::atof(next()));
		else if (a == "--table") table = next();
		else if (a == "--heads") heads = next();
		else if (a == "--params") list = true;
		else if (a == "-h" || a == "--help") { std::puts("see the header of render.cpp"); return 0; }
		else if (!a.empty() && a[0] == '-') die("unknown option " + a);
		else out = argv[i];
	}

	CommonState *s = (CommonState *)aliasing::create(sr, vs);
	if (list) {
		for (long i = 0; i < aliasing::num_params(); ++i) {
			t_param v; aliasing::getparameter(s, i, &v);
			std::printf("%-12s %g  [%g, %g]\n", aliasing::getparametername(s, i), v,
			            aliasing::getparametermin(s, i), aliasing::getparametermax(s, i));
		}
		return 0;
	}
	if (!out) die("no output file (render OUT.wav ...)");

	std::vector<ParamChange> changes;
	for (auto &a : sets) parse_assign(s, a, 0, changes);
	for (auto &t : ats) parse_assign(s, t.second, long(t.first * sr), changes);

	long frames = long(seconds * sr);
	std::vector<t_sample> in1(vs), in2(vs), o1(vs), o2(vs);
	t_sample *ins[2] = {in1.data(), in2.data()};
	t_sample *outs[2] = {o1.data(), o2.data()};
	std::vector<float> inter;
	inter.reserve(size_t(frames) * 2);

	for (long pos = 0; pos < frames; pos += vs) {
		long n = std::min<long>(vs, frames - pos);
		for (auto &c : changes)
			if (c.frame >= pos && c.frame < pos + vs) aliasing::setparameter(s, c.index, c.value, nullptr);
		for (long k = 0; k < n; ++k) {
			long fr = pos + k;
			double g = 0;
			for (auto &gt : gates) if (fr >= long(gt.first * sr) && fr < long(gt.second * sr)) g = 1;
			double y = 0;
			for (double t : syncs) if (fr == long(t * sr)) y = 1;
			in1[k] = g; in2[k] = y;
		}
		int err = aliasing::perform(s, ins, 2, outs, 2, n);
		if (err) die("perform returned error " + std::to_string(err));
		for (long k = 0; k < n; ++k) { inter.push_back(float(o1[k])); inter.push_back(float(o2[k])); }
	}

	write_wav(out, inter, sr);
	if (table) dump(table, aliasing::atab);
	if (heads) dump(heads, aliasing::aheads);
	aliasing::destroy(s);
	return 0;
}
