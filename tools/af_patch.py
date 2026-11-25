#!/usr/bin/env python3
"""The patcher: the English ROM from one's own dump of the cartridge, with a plain patch or a sealed one.

    python3 tools/af_patch.py apply ROM PATCH OUT [--iso DISC | --files DIR] [--ups NAFE_UPS]
    python3 tools/af_patch.py verify ROM PATCH EXPECTED [--iso DISC | --files DIR] [--ups NAFE_UPS]
    python3 tools/af_patch.py info PATCH
    python3 tools/af_patch.py seal ROM PATCH.bps OUT.afp --label TEXT [--disc NAME=FILE]... [--ups FILE]
    python3 tools/af_patch.py manifest ROM PATCH.bps PATCH.afp OUT.txt

ROM: the dump of Doubutsu no Mori, in any byte order. PATCH: a .bps (tools/bps.py; any BPS patcher applies
one) or a sealed patch (.afp). Standard library only: no build, no compiler.

Why a sealed patch. The English ROM holds, beside the cartridge's own bytes and this project's, what the
build made of two other things its maker owns: the disc of Animal Crossing (its English script, its font,
its signs, a model) and the AF Project's 2010 patch (menu labels, the title's logo, some messages). A .bps
carries all of that in the clear, and is for its maker's own use. A sealed patch is the same .bps with
every byte crossed with a keystream drawn from those very files: block i's key is the SHA-256 of a salt,
i and a window of the files' bytes, the window moving through all of them. No password and no hash opens
it; the files do. So it gives the ROM to someone who has the cartridge's dump, the same disc (GAFE01,
revision 0) and the same 2010 patch, and nothing to anyone else.

It is still a copy of that material, under a seal. Whether to hand one on is its maker's to decide, not
this tool's: reference/NOTES.md, "The patch (the deliverable)".

apply: PATCH's kind is read from its first bytes. A sealed one names the files it was sealed with (by
their place on the disc, their size and SHA-256): they are read from --iso (a plain disc image, .iso or
.gcm) or from --files (a directory with the files under their own names, as build/gc has them), and the
2010 patch from --ups. Every one is checked before anything is opened, the opened .bps against its own
SHA-256, and the ROM made against the MD5 the patch was sealed for.
"""

import hashlib
import json
import mmap
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bps  # noqa: E402
import gciso  # noqa: E402
import rom  # noqa: E402

MAGIC = b"AFP1\n"
WINDOW = 1024                               # bytes of the sealing files in each block's key
BLOCK = hashlib.sha256().digest_size
SPREAD = 2654435761                         # where block i's window starts: i times this, in the files' length


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def keystream(material, salt, size):
    """size bytes: block i is SHA-256(salt, i, a window of material that moves through all of it)."""
    if len(material) < WINDOW:
        raise ValueError("the sealing files are %d bytes, fewer than a window's %d" % (len(material), WINDOW))
    room, out = len(material) - WINDOW + 1, []
    for i in range((size + BLOCK - 1) // BLOCK):
        at = i * SPREAD % room
        out.append(hashlib.sha256(salt + struct.pack(">Q", i) + material[at:at + WINDOW]).digest())
    return b"".join(out)[:size]


def cross(data, stream):
    n = len(data)
    return (int.from_bytes(data, "big") ^ int.from_bytes(stream, "big")).to_bytes(n, "big") if n else b""


def seal(source, patch, keys, label):
    """The sealed patch of a .bps for source. keys: [(where from: "disc" or "ups", name, bytes)], in order."""
    target = bps.apply(source, patch)                   # a patch that does not apply is not sealed
    if not keys:
        raise ValueError("nothing to seal with")
    head = {
        "format": 1, "label": label,
        "source": {"md5": rom.md5(source), "size": len(source)},
        "target": {"md5": rom.md5(target), "sha256": sha256(target), "size": len(target)},
        "patch": {"sha256": sha256(patch), "size": len(patch)},
        "salt": sha256(patch)[:32],
        "window": WINDOW,
        "keys": [{"from": where, "name": name, "size": len(data), "sha256": sha256(data)} for where, name, data in keys],
    }
    text = json.dumps(head, sort_keys=True, indent=1).encode("utf-8")
    stream = keystream(b"".join(data for _, _, data in keys), bytes.fromhex(head["salt"]), len(patch))
    return MAGIC + struct.pack(">I", len(text)) + text + cross(patch, stream)


def header(sealed):
    if sealed[:len(MAGIC)] != MAGIC:
        raise ValueError("not a sealed patch")
    size = struct.unpack(">I", sealed[len(MAGIC):len(MAGIC) + 4])[0]
    start = len(MAGIC) + 4
    head = json.loads(sealed[start:start + size].decode("utf-8"))
    if head.get("format") != 1 or head.get("window") != WINDOW:
        raise ValueError("a sealed patch of another format (%r)" % head.get("format"))
    return head, sealed[start + size:]


def unseal(sealed, fetch):
    """The .bps inside. fetch(key) gives the bytes of one of the header's files, or raises ValueError."""
    head, body = header(sealed)
    parts = []
    for key in head["keys"]:
        data = fetch(key)
        if len(data) != key["size"] or sha256(data) != key["sha256"]:
            raise ValueError("%s is not the file this patch was sealed with (%d bytes, SHA-256 %s...; wanted %d, "
                             "%s...)" % (key["name"], len(data), sha256(data)[:12], key["size"], key["sha256"][:12]))
        parts.append(data)
    patch = cross(body, keystream(b"".join(parts), bytes.fromhex(head["salt"]), len(body)))
    if len(patch) != head["patch"]["size"] or sha256(patch) != head["patch"]["sha256"]:
        raise ValueError("the patch under the seal is damaged")
    return head, patch


def apply(source, patch, fetch=None):
    """(the ROM, the label or None): source patched, by a .bps or by a sealed patch and its files."""
    label = None
    if patch[:len(MAGIC)] == MAGIC:
        head, patch = unseal(patch, fetch)
        label = head["label"]
        if rom.md5(source) != head["source"]["md5"]:
            raise ValueError("this ROM is not the one the patch is for (MD5 %s, wanted %s)" % (
                rom.md5(source), head["source"]["md5"]))
    out = bps.apply(source, patch)
    if label is not None and rom.md5(out) != head["target"]["md5"]:
        raise ValueError("the ROM made is not the one the patch was sealed for")
    return out, label


def fetcher(iso=None, files=None, ups=None):
    """fetch for unseal: a disc's file from the image or from the directory, the 2010 patch from its file."""
    state = {}

    def fetch(key):
        if key["from"] == "ups":
            if not ups:
                raise ValueError("this patch was sealed with the 2010 patch too: --ups %s" % key["name"])
            return open(ups, "rb").read()
        if files:
            path = os.path.join(files, os.path.basename(key["name"]))
            if not os.path.exists(path):
                raise ValueError("%s has no %s" % (files, os.path.basename(key["name"])))
            return open(path, "rb").read()
        if not iso:
            raise ValueError("this patch is sealed with the disc's files: --iso DISC (or --files DIR)")
        if "disc" not in state:
            f = open(iso, "rb")
            state["disc"] = gciso.Disc(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ))
        try:
            return bytes(gciso.extract(state["disc"], key["name"]))
        except KeyError:
            raise ValueError("%s: no %s on this disc (%s)" % (iso, key["name"], state["disc"].game)) from None
    return fetch


def options(argv, names):
    opts, rest, i = {n: [] for n in names}, [], 0
    while i < len(argv):
        if argv[i] in opts:
            if i + 1 >= len(argv):
                raise SystemExit("af_patch: %s wants a value" % argv[i])
            opts[argv[i]].append(argv[i + 1])
            i += 2
        else:
            rest.append(argv[i])
            i += 1
    return opts, rest


def manifest(source, patch, sealed):
    head, _ = header(sealed)
    target = bps.apply(source, patch)
    crc = struct.unpack(">II", target[0x10:0x18])
    lines = [
        head["label"],
        "",
        "the cartridge's dump (.z64 order): %d bytes, MD5 %s" % (len(source), rom.md5(source)),
        "the English ROM:                   %d bytes, MD5 %s" % (len(target), rom.md5(target)),
        "                                   SHA-256 %s" % sha256(target),
        "                                   header CRCs %08X %08X" % crc,
        "the patch (.bps):                  %d bytes, SHA-256 %s" % (len(patch), sha256(patch)),
        "the sealed patch (.afp):           %d bytes, SHA-256 %s" % (len(sealed), sha256(sealed)),
        "",
        "the sealed patch opens with these, each as it is on the disc (Animal Crossing, GAFE01 revision 0) or in",
        "the AF Project's distribution:",
    ]
    lines += ["  %-5s %-40s %9d bytes  SHA-256 %s" % (k["from"], k["name"], k["size"], k["sha256"]) for k in head["keys"]]
    return "\n".join(lines) + "\n"


def main(argv):
    opts, args = options(argv, ("--iso", "--files", "--ups", "--disc", "--label"))
    one = {k: (v[-1] if v else None) for k, v in opts.items()}
    try:
        if len(args) == 4 and args[0] == "apply":
            source = rom.to_z64(open(args[1], "rb").read())
            out, label = apply(source, open(args[2], "rb").read(), fetcher(one["--iso"], one["--files"], one["--ups"]))
            open(args[3], "wb").write(out)
            print("%s: %d bytes, MD5 %s%s" % (args[3], len(out), rom.md5(out), " (%s)" % label if label else ""))
            return 0
        if len(args) == 4 and args[0] == "verify":
            source, want = rom.to_z64(open(args[1], "rb").read()), open(args[3], "rb").read()
            out, _ = apply(source, open(args[2], "rb").read(), fetcher(one["--iso"], one["--files"], one["--ups"]))
            if out != want:
                raise ValueError("%s does not give %s" % (args[2], args[3]))
            print("%s: gives %s, byte for byte (MD5 %s)" % (args[2], args[3], rom.md5(out)))
            return 0
        if len(args) == 2 and args[0] == "info":
            head, body = header(open(args[1], "rb").read())
            print(json.dumps(head, sort_keys=True, indent=1))
            return 0
        if len(args) == 4 and args[0] == "seal" and one["--label"]:
            keys = []
            for pair in opts["--disc"]:
                name, _, path = pair.partition("=")
                keys.append(("disc", name, open(path, "rb").read()))
            if one["--ups"]:
                keys.append(("ups", os.path.basename(one["--ups"]), open(one["--ups"], "rb").read()))
            source, patch = rom.to_z64(open(args[1], "rb").read()), open(args[2], "rb").read()
            sealed = seal(source, patch, keys, one["--label"])
            again, _ = apply(source, sealed, lambda key: next(d for w, n, d in keys if (w, n) == (key["from"], key["name"])))
            if again != bps.apply(source, patch):       # never write a seal that does not open to the ROM
                raise ValueError("the sealed patch does not give the ROM back")
            open(args[3], "wb").write(sealed)
            print("%s: %d bytes, sealed with %d files (%d bytes)" % (args[3], len(sealed), len(keys), sum(len(d) for _, _, d in keys)))
            return 0
        if len(args) == 5 and args[0] == "manifest":
            text = manifest(rom.to_z64(open(args[1], "rb").read()), open(args[2], "rb").read(), open(args[3], "rb").read())
            open(args[4], "w", encoding="utf-8").write(text)
            print("%s: %d lines" % (args[4], text.count("\n")))
            return 0
    except ValueError as e:
        raise SystemExit("af_patch: %s" % e)
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
