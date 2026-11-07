// regionspark.cpp -- Golly-free port of hotdogPi's one-spark oscillator search
// (ConwayLife.com forum, "Golly scripts" page 12, post of July 6th 2021).
//
// Works in any isotropic non-totalistic (Hensel) rule without B0, and in MAP
// rules (but MAP rules that are not D4/D8-symmetric break the script's
// assumption that symmetric sparks keep the pattern symmetric).
//
// Behaviour follows the original script line by line.  Differences:
//  * Golly's 32-bit g.hash() is replaced by exact comparison (box checks) or a
//    64-bit hash (shape snapshots); the original can mis-fire on 32-bit
//    collisions, this port (almost) can't.
//  * The author-specific parts of the posted script (catalyst "block broken"
//    cells, the row-exclusion rectangle, "x == 1 and y < 26" resume,
//    "x < 0 and y < 0" skip, the "already found" offset) are options, OFF by
//    default, as the author says to do for searches without catalysts.
//  * By default a find is printed and the search goes on (the inner loop stops;
//    the snapshot list is kept, so later sparks that evolve identically are
//    pruned as usual).  --stop exits at the first find, like the original.
//
// Coordinates are Golly's: x to the right, y downwards.  Rule index layout is
// MAP/Golly's: NW=256 N=128 NE=64 W=32 C=16 E=8 SW=4 S=2 SE=1.
//
// Build:  g++ -O2 -std=c++17 -fopenmp -o regionspark regionspark.cpp

#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <initializer_list>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _OPENMP
#include <omp.h>
#endif

using std::string;
using std::vector;

// ---------------------------------------------------------------- rule
static uint8_t RULE[512];   // Golly layout index -> next state
static uint8_t RULE2[512];  // index with each row triple bit-reversed (bit0 = west)

static int rev3(int t) { return ((t & 1) << 2) | (t & 2) | ((t >> 2) & 1); }

static int rot_cw(int x) {  // liferules::rotateBits90Clockwise
    return ((x & 0x4) << 6) | ((x & 0x20) << 2) | ((x & 0x100) >> 2) | ((x & 0x2) << 4) | (x & 0x10) |
           ((x & 0x80) >> 4) | ((x & 0x1) << 2) | ((x & 0x8) >> 2) | ((x & 0x40) >> 6);
}
static int flip_tb(int x) { return ((x & 0x07) << 6) | ((x & 0x1c0) >> 6) | (x & 0x38); }

static void set_sym(int x, int v) {
    for (int k = 0; k < 2; k++) {
        for (int i = 0; i < 4; i++) { RULE[x] = (uint8_t)v; x = rot_cw(x); }
        x = flip_tb(x);
    }
}

// Representatives taken from Golly's liferules.cpp (letters "ceaiknjqrytwz").
static const char *LETTERS = "ceaiknjqrytwz";
static const int REP[4][13] = {
    {1, 2},
    {5, 10, 3, 40, 33, 68},
    {69, 42, 11, 7, 98, 13, 14, 70, 41, 97},
    {325, 170, 15, 45, 99, 71, 106, 102, 43, 101, 105, 78, 108}};
static const int NLET[9] = {0, 2, 6, 10, 13, 10, 6, 2, 0};

static int rep_for(int n, int li) {  // neighbourhood (centre off) for n neighbours, letter li
    if (n <= 4) return REP[n - 1][li];
    return REP[8 - n - 1][li] ^ 0x1ef;
}

static void set_count(int n, int centre, int v) {
    for (int i = 0; i < 512; i++)
        if (((i >> 4) & 1) == centre && __builtin_popcount(i & 0x1ef) == n) RULE[i] = (uint8_t)v;
}

static void parse_part(const string &s, int centre) {
    size_t i = 0;
    while (i < s.size()) {
        if (!isdigit((unsigned char)s[i])) throw std::runtime_error("bad rule near '" + s.substr(i) + "'");
        int n = s[i++] - '0';
        if (n > 8) throw std::runtime_error("bad digit");
        bool neg = false;
        if (i < s.size() && s[i] == '-') { neg = true; i++; }
        string lets;
        while (i < s.size() && isalpha((unsigned char)s[i])) lets += (char)tolower(s[i++]);
        if (lets.empty()) {
            if (neg) throw std::runtime_error("'-' without letters");
            set_count(n, centre, 1);
            continue;
        }
        if (neg) set_count(n, centre, 1);
        for (char c : lets) {
            const char *p = strchr(LETTERS, c);
            int li = p ? int(p - LETTERS) : 99;
            if (li >= NLET[n]) throw std::runtime_error(string("letter '") + c + "' invalid for count " + std::to_string(n));
            set_sym(rep_for(n, li) | (centre << 4), neg ? 0 : 1);
        }
    }
}

static void parse_rule(const string &rule) {
    memset(RULE, 0, sizeof RULE);
    string r;
    for (char c : rule) if (!isspace((unsigned char)c)) r += c;
    if (r.size() > 3 && (r.compare(0, 3, "MAP") == 0 || r.compare(0, 3, "map") == 0)) {
        static const char *b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        string d = r.substr(3);
        int bit = 0;
        for (char c : d) {
            if (c == '=') break;
            const char *p = strchr(b64, c);
            if (!p) throw std::runtime_error("bad MAP char");
            int v = int(p - b64);
            for (int k = 5; k >= 0 && bit < 512; k--, bit++) RULE[bit] = (v >> k) & 1;  // bit 0 = index 0
        }
        if (bit < 512) throw std::runtime_error("MAP string too short");
        // MAP: first bit = all-zero neighbourhood; index order row-major NW..SE, weights 256..1
    } else {
        string lo;
        for (char c : r) lo += (char)tolower(c);
        size_t b = lo.find('b'), s = lo.find('s');
        if (b == string::npos || s == string::npos) throw std::runtime_error("rule must look like B3/S23-q4i");
        string bp, sp;
        auto grab = [&](size_t from) {
            size_t e = from + 1;
            while (e < r.size() && lo[e] != 'b' && lo[e] != 's' && lo[e] != '/') e++;
            return r.substr(from + 1, e - from - 1);
        };
        // letters b/s are not Hensel letters, so the first 'b'/'s' start the parts
        bp = grab(b);
        sp = grab(s);
        parse_part(bp, 0);
        parse_part(sp, 1);
    }
    if (RULE[0]) throw std::runtime_error("B0 rules are not supported");
    for (int i = 0; i < 512; i++) {
        int j = (rev3((i >> 6) & 7) << 6) | (rev3((i >> 3) & 7) << 3) | rev3(i & 7);
        RULE2[i] = RULE[j];
    }
}

// ---------------------------------------------------------------- cells
struct Cell { int x, y; };
static inline bool rowmajor(const Cell &a, const Cell &b) { return a.y != b.y ? a.y < b.y : a.x < b.x; }
static inline bool operator==(const Cell &a, const Cell &b) { return a.x == b.x && a.y == b.y; }
typedef vector<Cell> Cells;  // always kept row-major sorted (Golly getcells order)

struct Rect { int x, y, w, h; };

// ---------------------------------------------------------------- universe (32x32 tiles)
struct Tile { int tx, ty; uint32_t r[32]; };
static thread_local long g_steps = 0;  // generations simulated (for --trace)

class Univ {
  public:
    vector<Tile> t;
    vector<int> slot;  // open addressing, tile index + 1
    unsigned mask = 0;
    vector<Tile> nt;                     // scratch for step()
    vector<std::pair<int, int>> cand;    // scratch for step()

    static inline unsigned hkey(int tx, int ty) { return (unsigned)tx * 0x9E3779B1u ^ (unsigned)ty * 0x85EBCA77u; }
    void rehash() {
        unsigned n = 64;
        while (n < t.size() * 4) n <<= 1;
        if (slot.size() == n) std::fill(slot.begin(), slot.end(), 0);
        else slot.assign(n, 0);
        mask = n - 1;
        for (size_t i = 0; i < t.size(); i++) {
            unsigned h = hkey(t[i].tx, t[i].ty) & mask;
            while (slot[h]) h = (h + 1) & mask;
            slot[h] = (int)i + 1;
        }
    }
    int find(int tx, int ty) const {
        if (slot.empty()) return -1;
        unsigned h = hkey(tx, ty) & mask;
        while (slot[h]) {
            const Tile &q = t[slot[h] - 1];
            if (q.tx == tx && q.ty == ty) return slot[h] - 1;
            h = (h + 1) & mask;
        }
        return -1;
    }
    int get_or_add(int tx, int ty) {
        int i = find(tx, ty);
        if (i >= 0) return i;
        Tile nt;
        nt.tx = tx; nt.ty = ty;
        memset(nt.r, 0, sizeof nt.r);
        t.push_back(nt);
        if (t.size() * 2 > slot.size()) rehash();
        else {
            unsigned h = hkey(tx, ty) & mask;
            while (slot[h]) h = (h + 1) & mask;
            slot[h] = (int)t.size();
        }
        return (int)t.size() - 1;
    }
    void clear() { t.clear(); slot.clear(); mask = 0; }
    void setcell(int x, int y, int v) {
        if (v) {
            int i = get_or_add(x >> 5, y >> 5);
            t[i].r[y & 31] |= 1u << (x & 31);
        } else {
            int i = find(x >> 5, y >> 5);
            if (i >= 0) t[i].r[y & 31] &= ~(1u << (x & 31));
        }
    }
    int getcell(int x, int y) const {
        int i = find(x >> 5, y >> 5);
        return i >= 0 ? (t[i].r[y & 31] >> (x & 31)) & 1 : 0;
    }
    void put(const Cells &c, int dx = 0, int dy = 0) { for (auto &p : c) setcell(p.x + dx, p.y + dy, 1); }
    void load(const Cells &c) { clear(); put(c); }
    long pop() const {
        long n = 0;
        for (auto &q : t) for (int j = 0; j < 32; j++) n += __builtin_popcount(q.r[j]);
        return n;
    }
    bool empty() const {
        for (auto &q : t) for (int j = 0; j < 32; j++) if (q.r[j]) return false;
        return true;
    }
    bool rect(Rect &R) const {  // false if empty
        int x0 = INT32_MAX, y0 = INT32_MAX, x1 = INT32_MIN, y1 = INT32_MIN;
        for (auto &q : t) {
            uint32_t o = 0;
            int jlo = -1, jhi = -1;
            for (int j = 0; j < 32; j++) if (q.r[j]) { o |= q.r[j]; if (jlo < 0) jlo = j; jhi = j; }
            if (!o) continue;
            x0 = std::min(x0, q.tx * 32 + __builtin_ctz(o));
            x1 = std::max(x1, q.tx * 32 + 31 - __builtin_clz(o));
            y0 = std::min(y0, q.ty * 32 + jlo);
            y1 = std::max(y1, q.ty * 32 + jhi);
        }
        if (x0 == INT32_MAX) return false;
        R = {x0, y0, x1 - x0 + 1, y1 - y0 + 1};
        return true;
    }
    // cells inside rect (or all), row-major
    Cells cells() const {
        Cells c;
        for (auto &q : t)
            for (int j = 0; j < 32; j++)
                for (uint32_t b = q.r[j]; b; b &= b - 1) c.push_back({q.tx * 32 + __builtin_ctz(b), q.ty * 32 + j});
        std::sort(c.begin(), c.end(), rowmajor);
        return c;
    }
    Cells cells_in(const Rect &R) const {
        Cells c;
        int tx0 = R.x >> 5, tx1 = (R.x + R.w - 1) >> 5, ty0 = R.y >> 5, ty1 = (R.y + R.h - 1) >> 5;
        for (auto &q : t) {
            if (q.tx < tx0 || q.tx > tx1 || q.ty < ty0 || q.ty > ty1) continue;
            int bx = q.tx * 32, by = q.ty * 32;
            int jlo = std::max(0, R.y - by), jhi = std::min(31, R.y + R.h - 1 - by);
            int ilo = std::max(0, R.x - bx), ihi = std::min(31, R.x + R.w - 1 - bx);
            uint32_t m = (ihi == 31 ? 0xffffffffu : ((1u << (ihi + 1)) - 1)) & ~((1u << ilo) - 1);
            for (int j = jlo; j <= jhi; j++)
                for (uint32_t b = q.r[j] & m; b; b &= b - 1) c.push_back({bx + __builtin_ctz(b), by + j});
        }
        std::sort(c.begin(), c.end(), rowmajor);
        return c;
    }
    long count_in(const Rect &R) const {
        long n = 0;
        int tx0 = R.x >> 5, tx1 = (R.x + R.w - 1) >> 5, ty0 = R.y >> 5, ty1 = (R.y + R.h - 1) >> 5;
        for (auto &q : t) {
            if (q.tx < tx0 || q.tx > tx1 || q.ty < ty0 || q.ty > ty1) continue;
            int bx = q.tx * 32, by = q.ty * 32;
            int jlo = std::max(0, R.y - by), jhi = std::min(31, R.y + R.h - 1 - by);
            int ilo = std::max(0, R.x - bx), ihi = std::min(31, R.x + R.w - 1 - bx);
            uint32_t m = (ihi == 31 ? 0xffffffffu : ((1u << (ihi + 1)) - 1)) & ~((1u << ilo) - 1);
            for (int j = jlo; j <= jhi; j++) n += __builtin_popcount(q.r[j] & m);
        }
        return n;
    }
    bool any_in(const Rect &R) const {
        int tx0 = R.x >> 5, tx1 = (R.x + R.w - 1) >> 5, ty0 = R.y >> 5, ty1 = (R.y + R.h - 1) >> 5;
        for (auto &q : t) {
            if (q.tx < tx0 || q.tx > tx1 || q.ty < ty0 || q.ty > ty1) continue;
            int bx = q.tx * 32, by = q.ty * 32;
            int jlo = std::max(0, R.y - by), jhi = std::min(31, R.y + R.h - 1 - by);
            int ilo = std::max(0, R.x - bx), ihi = std::min(31, R.x + R.w - 1 - bx);
            uint32_t m = (ihi == 31 ? 0xffffffffu : ((1u << (ihi + 1)) - 1)) & ~((1u << ilo) - 1);
            for (int j = jlo; j <= jhi; j++) if (q.r[j] & m) return true;
        }
        return false;
    }
    void clear_outside(const Rect &R) {
        for (auto &q : t) {
            int bx = q.tx * 32, by = q.ty * 32;
            for (int j = 0; j < 32; j++) {
                if (!q.r[j]) continue;
                int y = by + j;
                if (y < R.y || y >= R.y + R.h) { q.r[j] = 0; continue; }
                int ilo = R.x - bx, ihi = R.x + R.w - 1 - bx;
                if (ihi < 0 || ilo > 31) { q.r[j] = 0; continue; }
                ilo = std::max(ilo, 0); ihi = std::min(ihi, 31);
                uint32_t m = (ihi == 31 ? 0xffffffffu : ((1u << (ihi + 1)) - 1)) & ~((1u << ilo) - 1);
                q.r[j] &= m;
            }
        }
    }

    void step() {
        g_steps++;
        nt.clear();
        // candidate tiles
        cand.clear();
        for (auto &q : t) {
            uint32_t o = 0;
            for (int j = 0; j < 32; j++) o |= q.r[j];
            if (!o) continue;
            bool up = q.r[0], dn = q.r[31], lf = o & 1, rt = o >> 31;
            cand.push_back({q.tx, q.ty});
            if (up) cand.push_back({q.tx, q.ty - 1});
            if (dn) cand.push_back({q.tx, q.ty + 1});
            if (lf) cand.push_back({q.tx - 1, q.ty});
            if (rt) cand.push_back({q.tx + 1, q.ty});
            if (q.r[0] & 1) cand.push_back({q.tx - 1, q.ty - 1});
            if (q.r[0] >> 31) cand.push_back({q.tx + 1, q.ty - 1});
            if (q.r[31] & 1) cand.push_back({q.tx - 1, q.ty + 1});
            if (q.r[31] >> 31) cand.push_back({q.tx + 1, q.ty + 1});
        }
        std::sort(cand.begin(), cand.end());
        cand.erase(std::unique(cand.begin(), cand.end()), cand.end());
        static const uint32_t Z[32] = {0};
        for (auto &cd : cand) {
            int tx = cd.first, ty = cd.second;
            const uint32_t *T[3][3];
            for (int dy = -1; dy <= 1; dy++)
                for (int dx = -1; dx <= 1; dx++) {
                    int i = find(tx + dx, ty + dy);
                    T[dy + 1][dx + 1] = i >= 0 ? t[i].r : Z;
                }
            uint64_t ext[34];
            for (int j = -1; j <= 32; j++) {
                int row = 1, jj = j;
                if (j < 0) { row = 0; jj = 31; }
                else if (j > 31) { row = 2; jj = 0; }
                ext[j + 1] = ((uint64_t)T[row][1][jj] << 1) | ((T[row][0][jj] >> 31) & 1) |
                             ((uint64_t)(T[row][2][jj] & 1) << 33);
            }
            Tile n;
            n.tx = tx; n.ty = ty;
            uint32_t any = 0;
            for (int j = 0; j < 32; j++) {
                uint64_t u = ext[j], m = ext[j + 1], d = ext[j + 2];
                uint64_t o = u | m | d;
                uint32_t act = (uint32_t)((o | (o >> 1) | (o >> 2)) & 0xffffffffu);
                uint32_t res = 0;
                while (act) {
                    int i = __builtin_ctz(act);
                    act &= act - 1;
                    int idx = (int)(((u >> i) & 7) << 6 | ((m >> i) & 7) << 3 | ((d >> i) & 7));
                    res |= (uint32_t)RULE2[idx] << i;
                }
                n.r[j] = res;
                any |= res;
            }
            if (any) nt.push_back(n);
        }
        t.swap(nt);
        rehash();
    }
};

static uint64_t shape_hash(const Univ &U) {  // translation-invariant (like g.hash(g.getrect()))
    Cells c = U.cells();
    if (c.empty()) return 0;
    int x0 = INT32_MAX, y0 = c[0].y;
    for (auto &p : c) x0 = std::min(x0, p.x);
    uint64_t h = 1469598103934665603ull;
    for (auto &p : c) {
        h = (h ^ (uint64_t)(uint32_t)(p.y - y0)) * 1099511628211ull;
        h = (h ^ (uint64_t)(uint32_t)(p.x - x0)) * 1099511628211ull;
    }
    return h ^ c.size();
}

// ---------------------------------------------------------------- RLE
static Cells parse_rle(const string &text) {
    Cells c;
    int x = 0, y = 0, n = 0;
    size_t i = 0;
    // skip header / comment lines
    string body;
    {
        size_t p = 0;
        while (p < text.size()) {
            size_t e = text.find('\n', p);
            if (e == string::npos) e = text.size();
            string line = text.substr(p, e - p);
            size_t k = line.find_first_not_of(" \t\r");
            if (k != string::npos && line[k] != '#' && !(line[k] == 'x' && line.find('=') != string::npos)) body += line;
            p = e + 1;
        }
    }
    for (i = 0; i < body.size(); i++) {
        char ch = body[i];
        if (isdigit((unsigned char)ch)) { n = n * 10 + (ch - '0'); continue; }
        int k = n ? n : 1;
        n = 0;
        if (ch == 'b' || ch == '.') x += k;
        else if (ch == 'o' || ch == 'A') { for (int q = 0; q < k; q++) c.push_back({x++, y}); }
        else if (ch == '$') { y += k; x = 0; }
        else if (ch == '!') break;
        else if (isspace((unsigned char)ch)) {}
        else throw std::runtime_error(string("unexpected RLE char ") + ch);
    }
    std::sort(c.begin(), c.end(), rowmajor);
    return c;
}

// With a frame, the RLE covers exactly that rectangle (leading blank rows/columns are
// written out), so RLEs written with the same frame line up when pasted at one spot.
static string to_rle(Cells c, const string &rule, const string &comment = "", const Rect *frame = nullptr) {
    if (c.empty() && !frame) return "x = 0, y = 0, rule = " + rule + "\n!\n";
    std::sort(c.begin(), c.end(), rowmajor);
    int x0 = INT32_MAX, x1 = INT32_MIN, y0 = 0, y1 = 0;
    if (frame) { x0 = frame->x; y0 = frame->y; x1 = frame->x + frame->w - 1; y1 = frame->y + frame->h - 1; }
    else {
        y0 = c.front().y; y1 = c.back().y;
        for (auto &p : c) { x0 = std::min(x0, p.x); x1 = std::max(x1, p.x); }
    }
    string out;
    if (!comment.empty()) out += "#C " + comment + "\n";
    out += "#CXRLE Pos=" + std::to_string(x0) + "," + std::to_string(y0) + "\n";  // absolute top-left
    out += "x = " + std::to_string(x1 - x0 + 1) + ", y = " + std::to_string(y1 - y0 + 1) + ", rule = " + rule + "\n";
    string body, line;
    auto emit = [&](int k, char ch) {
        string tok = (k > 1 ? std::to_string(k) : "") + ch;
        // no line breaks: RLE pattern data stays on one line
        line += tok;
    };
    int cy = y0;
    size_t i = 0;
    while (i < c.size()) {
        if (c[i].y > cy) { emit(c[i].y - cy, '$'); cy = c[i].y; }
        int cx = x0;
        while (i < c.size() && c[i].y == cy) {
            if (c[i].x > cx) { emit(c[i].x - cx, 'b'); cx = c[i].x; }
            int run = 0;
            while (i < c.size() && c[i].y == cy && c[i].x == cx + run) { run++; i++; }
            emit(run, 'o');
            cx += run;
        }
    }
    emit(1, '!');
    body += line + "\n";
    return out + body;
}

// ---------------------------------------------------------------- transforms (Golly select+rotate/flip+cut+paste(0,0))
static Cells normalize(Cells c) {
    if (c.empty()) return c;
    int x0 = INT32_MAX, y0 = INT32_MAX;
    for (auto &p : c) { x0 = std::min(x0, p.x); y0 = std::min(y0, p.y); }
    for (auto &p : c) { p.x -= x0; p.y -= y0; }
    std::sort(c.begin(), c.end(), rowmajor);
    return c;
}
static Cells cw(Cells c) { for (auto &p : c) { int x = p.x; p.x = -p.y; p.y = x; } return normalize(c); }
static Cells ccw(Cells c) { for (auto &p : c) { int x = p.x; p.x = p.y; p.y = -x; } return normalize(c); }
static Cells flipLR(Cells c) { for (auto &p : c) p.x = -p.x; return normalize(c); }
static Cells flipTB(Cells c) { for (auto &p : c) p.y = -p.y; return normalize(c); }
static Cells rot180(Cells c) { for (auto &p : c) { p.x = -p.x; p.y = -p.y; } return normalize(c); }

// ---------------------------------------------------------------- config
enum Mode { C2, C4, D4, X4, D8, C1 };  // C1: single copy, single spark (not in the original script)
struct Config {
    string rule = "B3/S23";
    Cells input;
    Mode mode = C2;
    int a = 1;
    bool rotate = false;
    bool range_set_x = false, range_set_y = false;
    int sx = 0, ex = 0, sy = 0, ey = 0;
    int gens = 500, gens2 = 2000;
    bool resume = false;
    int resume_x = 0, resume_y = 0;
    bool skip_negative = false;
    bool c4diag = true;
    vector<Cell> alive;  // "block broken" check cells
    bool keep = false;
    int keep_x = -50, keep_y = 14, keep_w = 100, keep_dh = -17;  // rect [kx, ky, kw, y+height+kdh]
    vector<Cell> known;  // "Already found" offsets
    bool stop = false;
    bool skip_unsparked = false;  // drop finds whose box returns without the spark (spark irrelevant)
    long max_finds = 0;           // 0 = no limit (per offset)
    vector<int> skip_periods;     // finds of these periods are dropped (e.g. the object's own oscillation)
    bool selfsym = false;         // C1: copy each spark by the pattern's own symmetries
    // sparks[L]: the sparks tried beside an edge run of L cells (index 4 = 4 or more). Each spark is a list
    // of row offsets from the run's top row, one cell each, in the column 2 left of the run.
    vector<vector<int>> sparks[5] = {
        {},
        {{-2, -1}, {-1, 0}, {0, 1}, {1, 2}},
        {{-1}, {0}, {2}, {-2, -1}, {-1, 0}, {1, 2}, {2, 3}},
        {{-1}, {0}, {1}, {2}, {3}, {-2, -1}, {-1, 0}, {2, 3}, {3, 4}},
        {{-1}, {0}, {1}, {2}, {3}, {4}, {-2, -1}, {-1, 0}, {0, 1}, {1, 2}, {2, 3}, {3, 4}, {4, 5}}};
    bool sparks_set = false;      // --sparks given (printed in the header)
    int threads = 0;
    bool quiet = false;
    bool trace = false;  // print every (x,y) visited, like g.show
};

struct State {  // r_* arrays + width/height for one z
    Cells r[8];
    int width, height;
};
// indices
enum { N_ = 0, E_, S_, W_, NE_, SE_, SW_, NW_ };
enum { UP = 0, DOWN = 1 };

struct Find { int x, y, period; bool same; };
struct Result {
    string text;
    bool found = false;
    long skipped = 0;   // finds dropped by --skip-unsparked
    vector<Find> finds;
};

static const char *mode_name(Mode m) { return m == C2 ? "C2" : m == C4 ? "C4" : m == D4 ? "D4" : m == X4 ? "X4" : m == C1 ? "C1" : "D8"; }

// one (x, y) offset: the body of the "for z" loop of the original
struct Task {
    int x, y;
    vector<std::pair<int, int>> zs;  // (z, index into states) actually visited, in order
};

static void search_xy(const Config &cf, const vector<State> &states, const Task &tk, Result &res, bool &stopflag) {
    const int x = tk.x, y = tk.y;
    const Mode mode = cf.mode;
    const int copies = mode == D8 ? 8 : mode == C2 ? 2 : mode == C1 ? 1 : 4;
    const int a = cf.a;
    char buf[512];
    for (auto &zz : tk.zs) {
        const int z = zz.first;
        const State &S = states[zz.second];
        const int width = S.width, height = S.height;
        Univ U;
        long num1;
        switch (mode) {
            case C1:
                U.put(S.r[N_], x, y); num1 = U.pop();
                break;
            case C2:
                U.put(S.r[DOWN], 0, 0); num1 = U.pop();
                U.put(S.r[UP], x, y);
                break;
            case C4:
                U.put(S.r[N_], x, y); num1 = U.pop();
                U.put(S.r[E_], y, -x - width + 1 - a);
                U.put(S.r[S_], -x - width + 1 - a, -y - height + 1 - a);
                U.put(S.r[W_], -y - height + 1 - a, x);
                break;
            case D4:
                U.put(S.r[SE_], x, y); num1 = U.pop();
                U.put(S.r[NE_], x, 0);
                U.put(S.r[NW_], 0, 0);
                U.put(S.r[SW_], 0, y);
                break;
            case X4:
                U.put(S.r[N_], x, y); num1 = U.pop();
                U.put(S.r[W_], 0, y - x - width + height);
                U.put(S.r[E_], x + y + width - 1, -width + 1);
                U.put(S.r[S_], y + height - 1, -x - width + 1);
                break;
            default:  // D8
                U.put(S.r[N_], x, y); num1 = U.pop();
                U.put(S.r[NE_], -x - width + 1 - a, y);
                U.put(S.r[E_], y, -x - width + 1 - a);
                U.put(S.r[SE_], y, x);
                U.put(S.r[S_], -x - width + 1 - a, -y - height + 1 - a);
                U.put(S.r[SW_], x, -y - height + 1 - a);
                U.put(S.r[W_], -y - height + 1 - a, x);
                U.put(S.r[NW_], -y - height + 1 - a, -x - width + 1 - a);
                break;
        }
        if (U.pop() != copies * num1) continue;
        Rect B;
        U.rect(B);
        if (cf.rotate && (B.w + B.h) % 2 == 1) continue;
        if (cf.trace) { snprintf(buf, sizeof buf, "visit %d %d %d\n", x, y, z); res.text += buf; }
        struct StepNote {  // with --trace, print generations simulated for this (x, y, z)
            const Config &cf; Result &res; long start;
            ~StepNote() { if (cf.trace) res.text += "steps " + std::to_string(g_steps - start) + "\n"; }
        } stepnote{cf, res, g_steps};
        const Cells P0 = U.cells();
        // C1 --selfsym: the starting pattern's own symmetries (about its bounding-box centre)
        vector<std::array<int, 4>> selfsyms;
        int sc2x = 0, sc2y = 0;
        if (mode == C1 && cf.selfsym) {
            sc2x = B.x + B.x + B.w - 1; sc2y = B.y + B.y + B.h - 1;
            static const int M8[8][4] = {{1,0,0,1},{0,-1,1,0},{-1,0,0,-1},{0,1,-1,0},{-1,0,0,1},{1,0,0,-1},{0,1,1,0},{0,-1,-1,0}};
            for (int k = 1; k < 8; k++) {
                Cells img;
                for (auto &q : P0) {
                    int X = 2 * q.x - sc2x, Y = 2 * q.y - sc2y;
                    int nx = M8[k][0] * X + M8[k][1] * Y + sc2x, ny = M8[k][2] * X + M8[k][3] * Y + sc2y;
                    if ((nx & 1) || (ny & 1)) { img.clear(); break; }
                    img.push_back({nx / 2, ny / 2});
                }
                std::sort(img.begin(), img.end(), rowmajor);
                if (img == P0) selfsyms.push_back({M8[k][0], M8[k][1], M8[k][2], M8[k][3]});
            }
        }
        Rect box1 = {B.x - 1, B.y - 1, B.w + 2, B.h + 2};
        Rect cbox = box1;  // box checked in the inner loop
        Cells ref1, ref2;
        for (auto &p : P0) ref1.push_back({p.x - box1.x, p.y - box1.y});
        if (!cf.rotate) {  // g.flip(0) about the selection's centre
            for (auto &p : P0) ref2.push_back({box1.x + box1.x + box1.w - 1 - p.x - box1.x, p.y - box1.y});
        } else {  // g.rotate(1) (anticlockwise), Golly's Selection::Rotate formulas
            int seltop = box1.y, selbottom = box1.y + box1.h - 1, selleft = box1.x, selright = box1.x + box1.w - 1;
            int halfht = (selbottom - seltop) / 2, halfwd = (selright - selleft) / 2;
            int midy = seltop + halfht, midx = selleft + halfwd;
            int nleft = midx + seltop - midy, nbottom = midy + selright - midx;
            Cells rp;
            for (auto &p : P0) rp.push_back({nleft + (p.y - seltop), nbottom - (p.x - selleft)});
            int x0 = INT32_MAX, y0 = INT32_MAX, x1 = INT32_MIN, y1 = INT32_MIN;
            for (auto &p : rp) { x0 = std::min(x0, p.x); x1 = std::max(x1, p.x); y0 = std::min(y0, p.y); y1 = std::max(y1, p.y); }
            cbox = {x0 - 1, y0 - 1, x1 - x0 + 3, y1 - y0 + 3};
            for (auto &p : rp) ref2.push_back({p.x - cbox.x, p.y - cbox.y});
        }
        std::sort(ref1.begin(), ref1.end(), rowmajor);
        std::sort(ref2.begin(), ref2.end(), rowmajor);
        auto box_match = [&](const Univ &V) -> int {
            long n = V.count_in(cbox);
            if (n != (long)ref1.size() && n != (long)ref2.size()) return 0;
            Cells c = V.cells_in(cbox);
            for (auto &p : c) { p.x -= cbox.x; p.y -= cbox.y; }
            if (c == ref1) return 1;
            if (c == ref2) return 2;
            return 0;
        };
        auto alive_ok = [&](const Univ &V) {
            for (auto &p : cf.alive) if (!V.getcell(p.x, p.y)) return false;
            return true;
        };

        std::deque<uint64_t> snaps(200, 0);  // generation_snapshots ('' never matches a hash)
        std::deque<bool> snapvalid(200, false);
        std::deque<long> recent_pops;
        for (int i = 100; i < 109; i++) recent_pops.push_back(i);
        std::deque<int> recent_min_x;
        for (int i = 100; i < 108; i++) recent_min_x.push_back(i);
        Cells current_gen;
        bool have_cur = false;
        int glider_deletions = 0;  // escaping gliders removed so far (for the report)

        for (int generation = 0; generation < cf.gens; generation++) {
            if (generation > 0) { U.load(current_gen); U.step(); }
            {
                Cells now = U.cells();
                if (have_cur && now == current_gen) break;
            }
            long pop = U.pop();
            recent_pops.push_back(pop); recent_pops.pop_front();
            if (pop < 4 * copies) break;
            if (pop > 125 * copies) break;
            if (*std::max_element(recent_pops.begin(), recent_pops.end()) ==
                *std::min_element(recent_pops.begin(), recent_pops.end())) break;
            if (!alive_ok(U)) break;
            for (int w = 0; w < 2; w++) {
                if (w == 1) U.load(current_gen);
                Cells temp = U.cells();
                if (cf.keep) {
                    Rect K = {cf.keep_x, cf.keep_y, cf.keep_w, y + height + cf.keep_dh};
                    if (K.h < 1) U.clear(); else U.clear_outside(K);
                    if (U.empty()) { U.put(temp); current_gen = U.cells(); have_cur = true; continue; }
                }
                Rect R = {0, 0, 0, 0};
                U.rect(R);
                int min_x = R.x;
                vector<int> edge;
                {
                    Cells col = U.cells_in({min_x, -40 + y, 1, 80});
                    for (auto &p : col) edge.push_back(p.y);
                }
                if (edge.empty()) { U.put(temp); current_gen = U.cells(); have_cur = true; continue; }
                auto contiguous = [&]() { return edge.back() - (int)edge.size() + 1 == edge.front(); };
                if (w == 1 && contiguous()) { U.put(temp); current_gen = U.cells(); have_cur = true; continue; }
                while (!contiguous()) {
                    if (w == 1) edge.pop_back(); else edge.erase(edge.begin());
                }
                U.put(temp);
                current_gen = U.cells(); have_cur = true;
                const int emin = edge.front();
                if (w == 0) {
                    recent_min_x.push_back(min_x); recent_min_x.pop_front();
                    if (U.any_in({min_x + 3, emin - 8, 3, 16})) recent_min_x.back() = 123;
                    bool glider = true;
                    for (int i = 0; i < 4; i++) if (recent_min_x[i] != recent_min_x[0]) glider = false;
                    for (int i = 4; i < 8; i++) if (recent_min_x[i] != recent_min_x[4]) glider = false;
                    if (glider && recent_min_x[4] == recent_min_x[0] - 1) {
                        for (int i = min_x; i < min_x + 3; i++)
                            for (int j = emin; j < emin + 3; j++) U.setcell(i, j, 0);
                        glider_deletions++;
                        current_gen = U.cells();
                        continue;
                    }
                }
                const vector<vector<int>> &sparks = cf.sparks[std::min((int)edge.size(), 4)];  // --sparks
                for (auto &spark : sparks) {
                    if (U.empty()) break;
                    U.load(current_gen);
                    int x1 = 0, y1 = 0;
                    Cells sparkcells;
                    for (int s1 : spark) {
                        int sy = s1 + emin;
                        vector<Cell> sc;
                        if (mode == C1) {
                            sc = {{min_x - 2, sy}};
                            for (auto &m : selfsyms) {   // --selfsym: images of the spark cell
                                int X = 2 * (min_x - 2) - sc2x, Y = 2 * sy - sc2y;
                                sc.push_back({(m[0] * X + m[1] * Y + sc2x) / 2, (m[2] * X + m[3] * Y + sc2y) / 2});
                            }
                        } else if (mode == C2) {
                            sc = {{min_x - 2, sy}, {-min_x + x + 1 + width, -s1 - emin + y - 1 + height}};
                        } else if (mode == C4 || mode == D8) {
                            sc = {{min_x - 2, sy}, {-min_x + 2 - a, -s1 - emin - a}, {-s1 - emin - a, min_x - 2}, {sy, -min_x + 2 - a}};
                        } else if (mode == D4) {
                            sc = {{min_x - 2, sy}, {-min_x + x + width + 1, -s1 + height + y - emin - 1},
                                  {min_x - 2, -s1 + height + y - emin - 1}, {-min_x + x + width + 1, sy}};
                        } else {  // X4; Python // is floor division
                            auto fdiv = [](int p, int q) { int d = p / q; if ((p % q != 0) && ((p < 0) != (q < 0))) d--; return d; };
                            int c0 = x + y + height - 1 + width, c1 = y - x - width + height + 1;
                            int ox = 2 * (min_x - 2) - c0, oy = 2 * sy - c1;
                            sc = {{fdiv(c0 - ox, 2) - 1, fdiv(c1 - oy, 2) - 1}, {fdiv(c0 - oy, 2) - 1, fdiv(c1 - ox, 2) - 1},
                                  {fdiv(c0 + ox, 2), fdiv(c1 + oy, 2)}, {fdiv(c0 + oy, 2), fdiv(c1 + ox, 2)}};
                        }
                        if (mode == D8) {
                            sc.push_back({min_x - 2, -s1 - emin - a});
                            sc.push_back({-min_x + 2 - a, sy});
                            sc.push_back({sy, min_x - 2});
                            sc.push_back({-s1 - emin - a, -min_x + 2 - a});
                        }
                        for (auto &p : sc) { U.setcell(p.x, p.y, 1); sparkcells.push_back(p); }
                        x1 = min_x - 5; y1 = sy;
                    }
                    vector<uint64_t> hash_list;
                    std::deque<long> recent_pops1;
                    for (int i = 100; i < 139; i++) recent_pops1.push_back(i);
                    for (int generation1 = 0; generation1 < cf.gens2; generation1++) {
                        U.step();
                        long p1 = U.pop();
                        if (!p1) break;
                        if (5 <= generation1 && generation1 <= 8) {
                            uint64_t h = shape_hash(U);
                            bool hit = false;
                            for (size_t i = 0; i < snaps.size(); i++) if (snapvalid[i] && snaps[i] == h) { hit = true; break; }
                            snaps.pop_front(); snapvalid.pop_front();
                            snaps.push_back(h); snapvalid.push_back(true);
                            if (hit) break;
                        }
                        recent_pops1.push_back(p1); recent_pops1.pop_front();
                        if (p1 > 125 * copies) break;
                        if (*std::max_element(recent_pops1.begin(), recent_pops1.end()) ==
                            *std::min_element(recent_pops1.begin(), recent_pops1.end())) break;
                        if (generation1 % 10 == 0) {
                            uint64_t h = shape_hash(U);
                            bool hit = std::find(hash_list.begin(), hash_list.end(), h) != hash_list.end();
                            hash_list.push_back(h);
                            if (hit) break;
                        }
                        if (!alive_ok(U)) break;
                        if (U.getcell(x1, y1)) break;
                        int mt = box_match(U);
                        if (mt && cf.skip_unsparked) {
                            // same generations without the spark: if the box matches anyway, the
                            // spark did nothing and this is not a partial
                            Univ V; V.load(current_gen);
                            for (int s2 = 0; s2 <= generation1; s2++) V.step();
                            if (box_match(V) == mt) { res.skipped++; break; }
                        }
                        if (mt && cf.max_finds && (long)res.finds.size() >= cf.max_finds) { res.skipped++; break; }
                        if (mt) {
                            int Pfind = (generation + generation1 + 1) * (mt == 1 ? 1 : 2);
                            bool skipit = false;  // the period or a multiple of it (same oscillation caught cycles later)
                            for (int q : cf.skip_periods) if (Pfind % q == 0) skipit = true;
                            if (skipit) { res.skipped++; break; }
                        }
                        if (mt) {
                            bool known = false;
                            for (auto &k : cf.known) if (k.x == x && k.y == y) known = true;
                            if (known) {
                                snprintf(buf, sizeof buf, "Already found: %d, %d, %d\n", x, y, generation);
                                res.text += buf;
                                std::fill(snapvalid.begin(), snapvalid.end(), false);
                                continue;
                            }
                            int T = generation + generation1 + 1;
                            string spk;
                            for (size_t i = 0; i < spark.size(); i++) spk += (i ? "," : "") + std::to_string(spark[i]);
                            snprintf(buf, sizeof buf,
                                     "Found!: %d, %d, %d  [z=%d w=%d edge=%d..%d spark=(%s) after=%d match=%s T=%d -> period %d]\n",
                                     x, y, generation, z, w, emin, edge.back(), spk.c_str(), generation1 + 1,
                                     mt == 1 ? "same" : (cf.rotate ? "rotated" : "flipped"), T, mt == 1 ? T : 2 * T);
                            res.text += buf;
                            res.found = true;
                            res.finds.push_back({x, y, mt == 1 ? T : 2 * T, mt == 1});
                            Cells withspark = current_gen;
                            for (auto &p : sparkcells) withspark.push_back(p);
                            std::sort(withspark.begin(), withspark.end(), rowmajor);
                            withspark.erase(std::unique(withspark.begin(), withspark.end()), withspark.end());
                            Cells sparkonly;
                            for (auto &p : withspark)
                                if (!std::binary_search(current_gen.begin(), current_gen.end(), p, rowmajor)) sparkonly.push_back(p);
                            Cells after = U.cells();
                            // common frame: union of everything shown
                            int fx0 = INT32_MAX, fy0 = INT32_MAX, fx1 = INT32_MIN, fy1 = INT32_MIN;
                            for (const Cells *cs : std::initializer_list<const Cells *>{&P0, &withspark, &after})
                                for (auto &p : *cs) { fx0 = std::min(fx0, p.x); fx1 = std::max(fx1, p.x); fy0 = std::min(fy0, p.y); fy1 = std::max(fy1, p.y); }
                            Rect F = {fx0, fy0, fx1 - fx0 + 1, fy1 - fy0 + 1};
                            long outside = (long)after.size() - U.count_in(cbox);
                            snprintf(buf, sizeof buf, "#C All RLEs of this find share one %dx%d frame (top-left %d,%d).\n",
                                     F.w, F.h, F.x, F.y);
                            res.text += buf;
                            snprintf(buf, sizeof buf, "#C Check box (initial bounding box + 1): cols %d..%d, rows %d..%d of the frame.\n",
                                     cbox.x - F.x, cbox.x + cbox.w - 1 - F.x, cbox.y - F.y, cbox.y + cbox.h - 1 - F.y);
                            res.text += buf;
                            if (glider_deletions) {
                                snprintf(buf, sizeof buf, "#C NOTE: %d escaping glider(s) were deleted before generation %d, so [1] run %d gens = [2] plus those gliders.\n",
                                         glider_deletions, generation, generation);
                                res.text += buf;
                            }
                            res.text += "#C Spark cells (col,row in the frame):";
                            for (auto &p : sparkonly) { snprintf(buf, sizeof buf, " (%d,%d)", p.x - F.x, p.y - F.y); res.text += buf; }
                            res.text += "\n";
                            res.text += to_rle(P0, cf.rule, "[1] generation 0: initial configuration", &F);
                            snprintf(buf, sizeof buf, "[2] generation %d: [1] after %d gens, before the spark", generation, generation);
                            res.text += to_rle(current_gen, cf.rule, buf, &F);
                            res.text += to_rle(sparkonly, cf.rule, "[3] the spark cells only", &F);
                            snprintf(buf, sizeof buf, "[4] = [2] + [3]: run this %d gens", generation1 + 1);
                            res.text += to_rle(withspark, cf.rule, buf, &F);
                            snprintf(buf, sizeof buf, "[5] generation %d: [4] after %d gens; the check box holds %s of [1]; %ld cell(s) outside the box",
                                     T, generation1 + 1, mt == 1 ? "a copy" : (cf.rotate ? "a 90-degree rotation" : "the mirror image"), outside);
                            res.text += to_rle(after, cf.rule, buf, &F);
                            if (cf.stop) { stopflag = true; return; }
                            break;
                        }
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------- main
static vector<Cell> parse_pairs(const string &s) {
    vector<Cell> v;
    size_t p = 0;
    while (p < s.size()) {
        size_t e = s.find(';', p);
        if (e == string::npos) e = s.size();
        string item = s.substr(p, e - p);
        int a, b;
        if (sscanf(item.c_str(), "%d,%d", &a, &b) == 2) v.push_back({a, b});
        p = e + 1;
    }
    return v;
}

// --sparks 'KEY:LIST;KEY:LIST...': KEY = 1, 2, 3, 4 (4 or more cells in the edge run) or * (all);
// LIST = sparks separated by spaces, each a comma-separated list of row offsets. Unlisted keys keep the default.
static void parse_sparks(const string &spec, Config &cf) {
    size_t i = 0;
    while (i <= spec.size()) {
        size_t j = spec.find(';', i);
        if (j == string::npos) j = spec.size();
        string g = spec.substr(i, j - i);
        i = j + 1;
        size_t b = g.find_first_not_of(" \t\r\n");
        if (b == string::npos) continue;
        size_t c = g.find(':');
        if (c == string::npos) throw std::runtime_error("--sparks: '" + g + "' needs KEY:LIST (KEY 1, 2, 3, 4 or *)");
        string key = g.substr(b, c - b);
        while (!key.empty() && isspace((unsigned char)key.back())) key.pop_back();
        int k0, k1;
        if (key == "*") k0 = 1, k1 = 4;
        else if (key == "1" || key == "2" || key == "3" || key == "4") k0 = k1 = key[0] - '0';
        else throw std::runtime_error("--sparks: key '" + key + "' must be 1, 2, 3, 4 (4 or more) or *");
        vector<vector<int>> list;
        string rest = g.substr(c + 1);
        size_t p = 0;
        while (true) {
            p = rest.find_first_not_of(" \t\r\n", p);
            if (p == string::npos) break;
            size_t q = rest.find_first_of(" \t\r\n", p);
            string tok = rest.substr(p, q == string::npos ? string::npos : q - p);
            p = q;
            vector<int> spark;
            size_t t = 0;
            while (t <= tok.size()) {
                size_t u = tok.find(',', t);
                if (u == string::npos) u = tok.size();
                string num = tok.substr(t, u - t);
                char *end = nullptr;
                long v = strtol(num.c_str(), &end, 10);
                if (num.empty() || *end || v < -1000 || v > 1000)
                    throw std::runtime_error("--sparks: bad row offset '" + num + "' in '" + tok + "'");
                spark.push_back((int)v);
                t = u + 1;
            }
            list.push_back(spark);
            if (q == string::npos) break;
        }
        for (int k = k0; k <= k1; k++) cf.sparks[k] = list;
    }
    cf.sparks_set = true;
}

static string sparks_text(const Config &cf) {
    string out;
    for (int k = 1; k <= 4; k++) {
        out += (k > 1 ? ";" : "") + std::to_string(k) + ":";
        for (size_t s = 0; s < cf.sparks[k].size(); s++) {
            out += s ? " " : "";
            for (size_t c = 0; c < cf.sparks[k][s].size(); c++) out += (c ? "," : "") + std::to_string(cf.sparks[k][s][c]);
        }
    }
    return out;
}

static void usage() {
    fprintf(stderr,
            "usage: regionspark --pattern RLE [options]\n"
            "  --rule R            Hensel rule, e.g. B3/S23-q4i, or MAP... (default B3/S23)\n"
            "  --pattern RLE       pattern RLE (header line optional); or --pattern-file F\n"
            "  --mode M            C2 C4 D4 X4 D8, or C1 (single copy, single spark; not in the original) (default C2)\n"
            "  --a N               C4/D8: 1 even, 0 odd symmetry (default 1)\n"
            "  --rotate            look for 90-degree rotation (half cycle) instead of mirror\n"
            "  --x A:B --y A:B     offset ranges (defaults per mode as in the script)\n"
            "  --gens N            outer generations (500)   --gens2 N  inner generations (2000)\n"
            "  --resume X,Y        skip x==X and y<Y (the script's 'x == 1 and y < 26' line)\n"
            "  --skip-negative     skip x<0 and y<0 (script's catalyst-on-two-sides line)\n"
            "  --no-c4-diag        disable C4 diagonal bounding (do this with catalysts)\n"
            "  --alive 'x,y;...'   cells that must stay alive (script's 'block broken' check)\n"
            "  --keep X0,Y0,W,DH   only spark rows in rect [X0,Y0,W,y+height+DH] (script: -50,14,100,-17)\n"
            "  --known 'x,y;...'   offsets already found: warn instead of reporting\n"
            "  --stop              exit at the first find (original behaviour)\n"
            "  --skip-unsparked    drop finds where the box also returns with no spark (not in the original)\n"
            "  --max-finds N       at most N reported finds per offset (not in the original)\n"
            "  --selfsym           C1 only: copy each spark by the pattern's own symmetries (not in the original)\n"
            "  --skip-period L     drop finds whose period is a multiple of one in L, e.g. 24 (not in the original)\n"
            "  --sparks SPEC       spark lists per edge-run length, e.g. '1:-2,-1 0,1;*:0 0,2' (see README; not in the original)\n"
            "  --threads N         OpenMP threads (default: all); use 1 to compare with the original\n"
            "  --trace             list every (x,y,z) actually searched\n");
    exit(1);
}

int main(int argc, char **argv) {
    Config cf;
    string patt;
    auto need = [&](int &i) -> string { if (i + 1 >= argc) usage(); return argv[++i]; };
    for (int i = 1; i < argc; i++) {
        string o = argv[i];
        if (o == "--rule") cf.rule = need(i);
        else if (o == "--pattern") patt = need(i);
        else if (o == "--pattern-file") {
            string f = need(i);
            FILE *fp = fopen(f.c_str(), "r");
            if (!fp) { perror(f.c_str()); return 1; }
            char b[4096]; size_t n;
            while ((n = fread(b, 1, sizeof b, fp)) > 0) patt.append(b, n);
            fclose(fp);
        } else if (o == "--mode") {
            string m = need(i);
            if (m == "C1") cf.mode = C1; else if (m == "C2") cf.mode = C2; else if (m == "C4") cf.mode = C4; else if (m == "D4") cf.mode = D4;
            else if (m == "X4") cf.mode = X4; else if (m == "D8") cf.mode = D8; else usage();
        } else if (o == "--a") cf.a = atoi(need(i).c_str());
        else if (o == "--rotate") cf.rotate = true;
        else if (o == "--x") { if (sscanf(need(i).c_str(), "%d:%d", &cf.sx, &cf.ex) != 2) usage(); cf.range_set_x = true; }
        else if (o == "--y") { if (sscanf(need(i).c_str(), "%d:%d", &cf.sy, &cf.ey) != 2) usage(); cf.range_set_y = true; }
        else if (o == "--gens") cf.gens = atoi(need(i).c_str());
        else if (o == "--gens2") cf.gens2 = atoi(need(i).c_str());
        else if (o == "--resume") { if (sscanf(need(i).c_str(), "%d,%d", &cf.resume_x, &cf.resume_y) != 2) usage(); cf.resume = true; }
        else if (o == "--skip-negative") cf.skip_negative = true;
        else if (o == "--no-c4-diag") cf.c4diag = false;
        else if (o == "--alive") cf.alive = parse_pairs(need(i));
        else if (o == "--keep") { if (sscanf(need(i).c_str(), "%d,%d,%d,%d", &cf.keep_x, &cf.keep_y, &cf.keep_w, &cf.keep_dh) != 4) usage(); cf.keep = true; }
        else if (o == "--known") cf.known = parse_pairs(need(i));
        else if (o == "--stop") cf.stop = true;
        else if (o == "--skip-unsparked") cf.skip_unsparked = true;
        else if (o == "--selfsym") cf.selfsym = true;
        else if (o == "--skip-period") { string v = need(i); for (auto &c : v) if (c == ',') c = ' ';
            char *e = &v[0]; while (*e) { long q = strtol(e, &e, 10); if (q > 0) cf.skip_periods.push_back((int)q); while (*e == ' ') e++; } }
        else if (o == "--max-finds") cf.max_finds = atol(need(i).c_str());
        else if (o == "--sparks") {
            try { parse_sparks(need(i), cf); } catch (std::exception &e) { fprintf(stderr, "error: %s\n", e.what()); return 1; }
        }
        else if (o == "--threads") cf.threads = atoi(need(i).c_str());
        else if (o == "--trace") cf.trace = true;
        else if (o == "--dump-rule") {  // testing: print the 512-entry table (Golly layout) and exit
            try { parse_rule(need(i)); } catch (std::exception &e) { printf("ERR %s\n", e.what()); return 0; }
            for (int k = 0; k < 512; k++) putchar('0' + RULE[k]);
            putchar('\n');
            return 0;
        }
        else usage();
    }
    if (patt.empty()) usage();
    try {
        parse_rule(cf.rule);
        cf.input = parse_rle(patt);
    } catch (std::exception &e) {
        fprintf(stderr, "error: %s\n", e.what());
        return 1;
    }
    if (cf.input.empty()) { fprintf(stderr, "empty pattern\n"); return 1; }

    // width/height = bounding box of the input put at (0,0)
    int ix0 = INT32_MAX, ix1 = INT32_MIN, iy0 = INT32_MAX, iy1 = INT32_MIN;
    for (auto &p : cf.input) { ix0 = std::min(ix0, p.x); ix1 = std::max(ix1, p.x); iy0 = std::min(iy0, p.y); iy1 = std::max(iy1, p.y); }
    int width = ix1 - ix0 + 1, height = iy1 - iy0 + 1;

    // rotations and reflections, as in the script
    State st;
    st.width = width; st.height = height;
    const Mode mode = cf.mode;
    if (mode == C1) {
        st.r[N_] = cf.input;
    } else if (mode == C2) {
        st.r[UP] = cf.input;
        st.r[DOWN] = rot180(cf.input);
    } else if (mode == C4 || mode == X4 || mode == D8) {
        st.r[N_] = cf.input;
        if (mode == X4) {
            st.r[E_] = cw(flipTB(st.r[N_]));
            st.r[S_] = ccw(flipTB(st.r[E_]));
            st.r[W_] = cw(flipTB(st.r[S_]));
        } else {
            st.r[E_] = ccw(st.r[N_]);
            st.r[S_] = ccw(st.r[E_]);
            st.r[W_] = ccw(st.r[S_]);
        }
        if (mode == D8) {
            st.r[NW_] = rot180(flipLR(st.r[W_]));
            st.r[NE_] = ccw(st.r[NW_]);
            st.r[SE_] = ccw(st.r[NE_]);
            st.r[SW_] = ccw(st.r[SE_]);
        }
    } else {  // D4
        st.r[SE_] = cf.input;
        st.r[NE_] = flipTB(st.r[SE_]);
        st.r[NW_] = flipLR(st.r[NE_]);
        st.r[SW_] = flipTB(st.r[NW_]);
    }
    // The script permutes r_* (and for C4/D8 swaps width/height) at each z, after the
    // C4 diagonal test, which uses the current width.  When that test fails the
    // permutation is skipped, so for non-square patterns in C4 the state drifts from
    // one (x, y) to the next.  Replay that state machine serially, in loop order.
    int nz = (mode == C2 || mode == X4) ? 1 : mode == D8 ? 8 : 4;
    auto advance = [&](State &s, int z) {
        if (mode == C4) {
            std::swap(s.width, s.height);
            Cells n = s.r[N_], e = s.r[E_], so = s.r[S_], w = s.r[W_];
            s.r[N_] = e; s.r[E_] = so; s.r[S_] = w; s.r[W_] = n;
        }
        if (mode == D8) {
            Cells o[8];
            for (int k = 0; k < 8; k++) o[k] = s.r[k];
            if (z % 4 == 0) {
                s.r[N_] = o[NE_]; s.r[E_] = o[SE_]; s.r[S_] = o[SW_]; s.r[W_] = o[NW_];
                s.r[NE_] = o[N_]; s.r[SE_] = o[E_]; s.r[SW_] = o[S_]; s.r[NW_] = o[W_];
                for (int k = 0; k < 8; k++) o[k] = s.r[k];
            }
            std::swap(s.width, s.height);
            s.r[N_] = o[W_]; s.r[E_] = o[N_]; s.r[S_] = o[E_]; s.r[W_] = o[S_];
            s.r[NE_] = o[SE_]; s.r[SE_] = o[SW_]; s.r[SW_] = o[NW_]; s.r[NW_] = o[NE_];
        }
        if (mode == D4) {
            Cells se = s.r[SE_], ne = s.r[NE_], nw = s.r[NW_], sw = s.r[SW_];
            if (z % 2 == 0) { s.r[SE_] = ne; s.r[NE_] = se; s.r[NW_] = sw; s.r[SW_] = nw; }
            else { s.r[SE_] = sw; s.r[NE_] = nw; s.r[NW_] = ne; s.r[SW_] = se; }
        }
    };
    vector<State> states;
    auto state_index = [&](const State &s) {
        for (size_t i = 0; i < states.size(); i++) {
            bool eq = states[i].width == s.width && states[i].height == s.height;
            for (int k = 0; k < 8 && eq; k++) eq = states[i].r[k] == s.r[k];
            if (eq) return (int)i;
        }
        states.push_back(s);
        return (int)states.size() - 1;
    };

    // bounds
    int sx, ex, sy, ey;
    switch (mode) {
        case C1: sx = 0; ex = 0; sy = 0; ey = 0; break;  // one copy: the offset doesn't matter
        case C2: sx = -20; ex = 20; sy = -20; ey = 20; break;
        case C4: sx = -15; ex = 15; sy = 0; ey = 10; break;
        case D4: sx = width + 1; ex = width + 15; sy = height + 1; ey = height + 15; break;
        case X4: sx = -20; ex = 20; sy = -20; ey = 15; break;
        default: sx = 0; ex = 15; sy = 0; ey = 15; break;
    }
    if (cf.range_set_x) { sx = cf.sx; ex = cf.ex; }
    if (cf.range_set_y) { sy = cf.sy; ey = cf.ey; }

    // task list in the script's loop order
    vector<Task> tasks;
    {
        State s = st;
        for (int x = sx; x <= ex; x++)
            for (int y = sy; y <= ey; y++) {
                // z-independent skips: every z continues, so the state is untouched
                if (cf.resume && x == cf.resume_x && y < cf.resume_y) continue;
                if (cf.skip_negative && x < 0 && y < 0) continue;
                if (mode == D8 && y > x) continue;
                Task tk{x, y, {}};
                if (mode == C1) {  // the 8 orientations of the pattern (duplicates skipped)
                    Cells o[8] = {cf.input, cw(cf.input), rot180(cf.input), ccw(cf.input),
                                  flipLR(cf.input), flipLR(cw(cf.input)), flipTB(cf.input), flipLR(ccw(cf.input))};
                    vector<Cells> seen_o;
                    for (int z = 0; z < 8; z++) {
                        Cells n = normalize(o[z]);
                        if (std::find(seen_o.begin(), seen_o.end(), n) != seen_o.end()) continue;
                        seen_o.push_back(n);
                        State s1 = st; s1.r[N_] = n;
                        int x1 = INT32_MIN, y1 = INT32_MIN;
                        for (auto &q : n) { x1 = std::max(x1, q.x); y1 = std::max(y1, q.y); }
                        s1.width = x1 + 1; s1.height = y1 + 1;
                        tk.zs.push_back({z, state_index(s1)});
                    }
                    tasks.push_back(tk);
                    continue;
                }
                for (int z = 0; z < nz; z++) {
                    if (mode == C4 && cf.c4diag && !(-y - s.width <= x && x < y)) continue;
                    advance(s, z);
                    tk.zs.push_back({z, state_index(s)});
                }
                if (!tk.zs.empty()) tasks.push_back(tk);
            }
    }

    printf("# regionspark: rule %s, mode %s%s, x %d..%d, y %d..%d, %zu offsets, gens %d/%d\n", cf.rule.c_str(),
           mode_name(mode), cf.rotate ? " rotate" : "", sx, ex, sy, ey, tasks.size(), cf.gens, cf.gens2);
    if (cf.sparks_set) printf("# sparks: %s\n", sparks_text(cf).c_str());
    printf("%s", to_rle(cf.input, cf.rule, "input pattern").c_str());
    fflush(stdout);

#ifdef _OPENMP
    if (cf.threads > 0) omp_set_num_threads(cf.threads);
#endif
    vector<Result> results(tasks.size());
    vector<char> done(tasks.size(), 0);
    size_t printed = 0;
    long firststop = -1;
    int nfound = 0;
#pragma omp parallel for schedule(dynamic, 1)
    for (long ti = 0; ti < (long)tasks.size(); ti++) {
        bool skip;
#pragma omp critical(st)
        skip = firststop >= 0 && ti > firststop;
        bool stopflag = false;
        if (!skip) search_xy(cf, states, tasks[ti], results[ti], stopflag);
#pragma omp critical(st)
        {
            if (stopflag && (firststop < 0 || ti < firststop)) firststop = ti;
            done[ti] = 1;
            while (printed < tasks.size() && done[printed]) {
                if (firststop >= 0 && (long)printed > firststop) { printed = tasks.size(); break; }
                fputs(results[printed].text.c_str(), stdout);
                if (results[printed].found) nfound++;
                printed++;
            }
            fflush(stdout);
            if (!cf.quiet) fprintf(stderr, "\r%zu/%zu offsets done", printed, tasks.size());
        }
    }
    if (!cf.quiet) fprintf(stderr, "\n");
    // summary: distinct (x, y, period) with the number of spark configurations
    vector<std::pair<Find, int>> sum;
    for (size_t i = 0; i < printed && i < results.size(); i++)
        for (auto &f : results[i].finds) {
            bool hit = false;
            for (auto &q : sum)
                if (q.first.x == f.x && q.first.y == f.y && q.first.period == f.period && q.first.same == f.same) { q.second++; hit = true; }
            if (!hit) sum.push_back({f, 1});
        }
    for (auto &q : sum)
        printf("# summary: offset %d,%d period %d (%s) from %d spark configuration(s)\n", q.first.x, q.first.y,
               q.first.period, q.first.same ? "returns" : "flips/rotates", q.second);
    long nskipped = 0;
    for (size_t i = 0; i < printed && i < results.size(); i++) nskipped += results[i].skipped;
    if (cf.skip_unsparked || cf.max_finds || !cf.skip_periods.empty()) printf("# skipped: %ld find(s) (--skip-unsparked / --max-finds / --skip-period)\n", nskipped);
    printf("# done: %d offset(s) with finds\n", nfound);
    return 0;
}
