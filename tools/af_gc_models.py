#!/usr/bin/env python3
"""The GameCube's models held to the cartridge's (local: prints only, writes nothing).

    python3 tools/af_gc_models.py furniture ROM REL_SZS MAP        each of the cartridge's pieces of furniture
    python3 tools/af_gc_models.py world ROM REL_SZS MAP [FAMILY]   every vertex array of the GameCube's module

ROM: the user's dump (.z64). REL_SZS and MAP: build/gc's copies of the disc's module and of its map (make
script's).

The English names and words are the GameCube's, and the GameCube's game drew some things anew: a name at a
number can be another drawing's. tools/af_items.py pairs compares the names, and the second review looked at
the clothes', the floors' and the walls' textures; this compares the models. The GameCube's lists draw the
N64's vertices (16 bytes: a place, a flag, a texture's place, a colour or a normal), and a model the two
games share has the same vertices but for the flag. So:

furniture: for each of the cartridge's 947 pieces, the GameCube's piece its name comes from
(af_items.gc_source), that piece's profile (the table of 1,266 pointers the map puts under ac_my_room.o's
furniture_quality), the vertex arrays the profile reaches through the module's own relocations, and how many
of their vertices are in the cartridge's object of the piece (the one its overlay's profile names). Prints
how many pieces have every vertex there, and the others: those whose GameCube place holds its placeholder
(the GameCube's game no longer has the piece, its table of names still has the name), and those with another
model, each with the share of it that is the same.

world: every vertex array of the module (the names ending in _v), looked for in the cartridge's files;
prints by family (the name's first part: obj the structures', int the furniture's, act and tol the things in
the hand and on the ground, three letters a kind of animal) how many are whole in the cartridge, in part or
not there, and with FAMILY the names of that family's arrays that are not whole.

A model that differs is not a fault: the GameCube's game has things the cartridge has not, and drew much of
its own again. It is where to look: at the piece in the running game, beside its name. What the look found is
in reference/NOTES.md, "The shrine and two paintings".
"""

import collections
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import af_gc_nes  # noqa: E402
import af_gc_signs  # noqa: E402
import af_items  # noqa: E402
import gciso  # noqa: E402
import nafe_diff  # noqa: E402

PROFILES = ("furniture_quality", "ac_my_room.o")    # the table of the pieces' profiles, where the map has it
PLACEHOLDER = "iam_dummy"                           # the profile of a place the GameCube's game has no piece for
VERTEX = 16
REACH = 9                                           # a profile to its vertices: functions, a rig, its lists
BIG = 0x4000                                        # nothing a piece owns is larger; a shared table is


def same_vertex(a):
    """A vertex without its flag (bytes 6 and 7: 0 in the cartridge's, 1 in the GameCube's)."""
    return a[:6] + a[8:16]


class GameCube:
    def __init__(self, rel_szs, map_text):
        self.m = af_gc_nes.Module(gciso.yaz0(rel_szs), map_text)
        self.at = {}
        for name, number in af_gc_nes.SECTIONS.items():
            for o, s, sym, ob in self.m.layout.get(name, ()):
                if s and not sym.startswith("."):
                    self.at[(sym, ob)] = (name, number, o, s)

    def bytes(self, sym, ob):
        name, _, o, s = self.at[(sym, ob)]
        base = self.m.sections[af_gc_nes.SECTIONS[name]][0] & ~3
        return self.m.rel[base + o:base + o + s]

    def profiles(self):
        """The profile each of the table's places names: [(name, object) or None]."""
        _, size = self.m.find(".data", *PROFILES)
        out = []
        for j in range(size // 4):
            what = self.m.target(".data", PROFILES[0], PROFILES[1], 4 * j)
            out.append((what[0], what[1]) if what else None)
        return out

    def vertices(self, sym, ob):
        """The vertex arrays the symbol reaches through the module's relocations: {(name, object)}. A
        function's calls are not followed (what it names in the data is)."""
        seen, queue, out = {(sym, ob)}, [(sym, ob, 0)], set()
        text = af_gc_nes.SECTIONS[".text"]
        while queue:
            n, o_, depth = queue.pop()
            if (n, o_) not in self.at:
                continue
            name, number, start, size = self.at[(n, o_)]
            if is_vertices(n):
                out.add((n, o_))
                continue
            if depth >= REACH or size > BIG:
                continue
            for pos in range(start, start + size):
                hit = self.m.relocs.get((number, pos))
                if hit is None or (number == text and hit[1] == text):
                    continue
                what = self.m.named(hit[1], hit[2])
                if what and (what[0], what[1]) not in seen:
                    seen.add((what[0], what[1]))
                    queue.append((what[0], what[1], depth + 1))
        return out


def is_vertices(name):
    return re.search(r"_v\d*$|_vtx$", name) is not None


def cart_objects(rom):
    """{piece: the object its overlay's profile names, or None}: the profile is where three words of the
    overlay are a file's start, its end and the segment the room draws an object at."""
    room = af_gc_signs.file_at(rom, af_gc_nes.MY_ROOM_VROM)
    files = {e[0]: e for e in nafe_diff.dma_entries(rom)}
    out, cache = {}, {}
    for piece in range(next(n for k, n, _, _, _ in af_items.KINDS if k == "ftr")):
        at = af_gc_nes.OVERLAY_TABLE - af_gc_nes.MY_ROOM_VRAM + 16 * piece
        vrom = struct.unpack(">I", room[at:at + 4])[0]
        out[piece] = None
        if vrom not in files:
            continue
        if vrom not in cache:
            cache[vrom] = nafe_diff.file_data(rom, files[vrom])
        ovl = cache[vrom]
        for off in range(0, len(ovl) - 11, 4):
            start, end, seg = struct.unpack(">3I", ovl[off:off + 12])
            if seg == af_gc_nes.SEG and start in files and files[start][1] == end:
                out[piece] = nafe_diff.file_data(rom, files[start])
                break
    return out


def furniture(rom, gc):
    profiles = gc.profiles()
    objects = cart_objects(rom)
    same, gone, other, unread, elsewhere = 0, [], [], [], 0
    for piece, obj in sorted(objects.items()):
        src = af_items.gc_source("ftr", piece)
        if src is None or src[0] != "ftr":
            elsewhere += 1                              # the clothes shown as furniture: the clothes' names
            continue
        profile = profiles[src[1]] if src[1] < len(profiles) else None
        if profile is None or obj is None:
            unread.append(piece)
            continue
        if profile[0] == PLACEHOLDER:
            gone.append(piece)
            continue
        have = {same_vertex(obj[k:k + VERTEX]) for k in range(0, len(obj) - VERTEX + 1, 8)}
        count = there = 0
        for sym, ob in gc.vertices(*profile):
            raw = gc.bytes(sym, ob)
            count += len(raw) // VERTEX
            there += sum(1 for k in range(0, len(raw) - VERTEX + 1, VERTEX) if same_vertex(raw[k:k + VERTEX]) in have)
        if count and there == count:
            same += 1
        else:
            other.append((there / count if count else 0.0, piece, src[1], profile[0], there, count))
    print("af_gc_models: %d pieces: %d with every vertex of the GameCube's piece, %d the GameCube has a "
          "placeholder for, %d with another model, %d not compared (no object of their own found), %d the "
          "clothes'" % (len(objects), same, len(gone), len(other), len(unread), elsewhere))
    print("the GameCube's placeholder: %s" % ", ".join(str(p) for p in gone))
    print("not compared: %s" % ranges(unread))
    for share, piece, j, name, there, count in sorted(other):
        print("  %3d%%  piece %3d (the GameCube's %4d, %s): %d of %d vertices" % (
            round(share * 100), piece, j, name, there, count))
    return 0


def ranges(numbers):
    out, run = [], []
    for n in numbers + [None]:
        if run and n is not None and n == run[-1] + 1:
            run.append(n)
            continue
        if run:
            out.append("%d-%d" % (run[0], run[-1]) if len(run) > 1 else str(run[0]))
        run = [n]
    return ", ".join(out) or "none"


def world(rom, gc, family=None):
    image = b"".join(nafe_diff.file_data(rom, e) for e in nafe_diff.dma_entries(rom))
    tally, listed = collections.defaultdict(lambda: [0, 0, 0]), []
    base = gc.m.sections[af_gc_nes.SECTIONS[".data"]][0] & ~3
    for start, size, sym, ob in sorted(gc.m.layout[".data"]):      # every one: a name can be there twice
        if not is_vertices(sym) or size < 3 * VERTEX or size % VERTEX:
            continue
        raw = gc.m.rel[base + start:base + start + size]
        count, best = len(raw) // VERTEX, 0
        for first in (0, count // 2):                   # a run of the array found from its first or middle vertex
            key = raw[VERTEX * first:VERTEX * first + 6]
            at, tries = image.find(key), 0
            while at >= 0 and tries < 40 and best < count:
                if image[at + 8:at + VERTEX] == raw[VERTEX * first + 8:VERTEX * (first + 1)]:
                    lead = at - VERTEX * first
                    best = max(best, sum(1 for k in range(count) if lead + VERTEX * k >= 0 and same_vertex(
                        image[lead + VERTEX * k:lead + VERTEX * (k + 1)]) == same_vertex(raw[VERTEX * k:VERTEX * (k + 1)])))
                at, tries = image.find(key, at + 1), tries + 1
        fam = sym.split("_")[0]
        tally[fam][0 if best == count else 2 if best == 0 else 1] += 1
        if fam == family and best != count:
            listed.append("%s %d/%d" % (sym, best, count))
    total = [sum(v[k] for v in tally.values()) for k in range(3)]
    print("af_gc_models: %d vertex arrays in the GameCube's module: %d whole in the cartridge, %d in part, %d "
          "not there" % (sum(total), total[0], total[1], total[2]))
    for fam, (whole, part, none) in sorted(tally.items(), key=lambda kv: -sum(kv[1])):
        if whole + part + none >= 4 or fam == family:
            print("  %-8s %4d whole %4d in part %4d not there" % (fam, whole, part, none))
    if family:
        print("%s, not whole: %s" % (family, "; ".join(listed) or "none"))
    return 0


def main(argv):
    if len(argv) not in (4, 5) or argv[0] not in ("furniture", "world") or (argv[0] == "furniture" and len(argv) == 5):
        raise SystemExit(__doc__)
    rom = open(argv[1], "rb").read()
    gc = GameCube(open(argv[2], "rb").read(), open(argv[3], errors="replace").read())
    if argv[0] == "furniture":
        return furniture(rom, gc)
    return world(rom, gc, argv[4] if len(argv) == 5 else None)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
