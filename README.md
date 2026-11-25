# Animal Forest (N64) in English

An English version of **Doubutsu no Mori** (どうぶつの森, Nintendo 64, 2001, released
only in Japan), made by **recompiling the game from its decompiled source**
instead of patching the ROM by hand.

Version 1.0. Everything the game shows is in English: the dialogue, the
answers, the letters, the menus, the items' names, the signs on the
buildings. It has been played and measured on emulators; it has not yet been
run on a real console.

*En español, con toda la historia del proyecto: [README.es.md](README.es.md).
The verified facts, with their sources: [reference/NOTES.md](reference/NOTES.md).*

## Why recompile

The translation that existed, the AF Project's (Zoinkity; last patch
2010-12-02), patched the ROM's machine code directly. Text boxes, names and
items could be made longer, but not the buffers the text lands in, because
that would move everything behind them in memory. Its own documentation
calls it a work in progress, and it has a known hang later in the game.

Today there is [zeldaret/af](https://github.com/zeldaret/af), the game's
decompilation: it takes code and data out of your ROM, compiles the code
from C and produces a ROM **identical byte for byte**. With that, a larger
buffer is a constant changed, and the linker moves the rest. And the
GameCube's Animal Crossing, whose English is Nintendo's own, is the same
game one generation later.

So this project:

- rebuilds the cartridge from source and proves the result identical
  (`make verify`);
- moves the system's code to the end of the ROM, where it can grow, without
  moving anything in RAM;
- reads the official English from **your own disc** of Animal Crossing at
  build time, message by message, and gives each one the cartridge's control
  codes;
- translates the rest itself, from the cartridge's Japanese.

## What is in the English ROM

- **The dialogue**: 11,752 messages. About nine in ten (10,498) are
  Nintendo's own English from the GameCube, 96 come from the AF Project's
  patch, and the rest, some 1,150, are this project's.
- **A proportional font** (the GameCube's letters and widths), with every
  window, menu and board laid out by measured width.
- **Longer text where English needs it**: letters and notices of 192 bytes
  for the cartridge's 96, item names of 16 letters for 10, animals' names
  and catchphrases past the cartridge's 6 and 4 bytes. The save keeps what
  does not fit the cartridge's own layout beside it, and a Controller Pak
  carries it on a trip to another town.
- **The items' names** (1,703), the menus' words, the name-entry dial with
  small letters, Mr. Resetti's phrases typed in English.
- **The signs**: the shops' and the stalls' boards redrawn in English, and
  words on seventeen pieces of furniture.
- **The NES**: the cartridge's eight Famicoms drawn as the GameCube's NES,
  each named after its game.

It is the Japanese cartridge in English, not Animal Crossing: its festivals
are the cartridge's, and the building in the plaza is a shrine. Where the
GameCube's English spoke of something the cartridge does not have or draws
otherwise, the text names what is there (NOTES, "The shrine and two
paintings").

## What you need

- **Your own dump** of Doubutsu no Mori (NUS-NAFJ-JPN, 16 MiB, MD5
  `a4f7c57c180297b2e7ba5a5feb44fe0b` in `.z64` order; any byte order is
  accepted).
- **Your own disc image** of Animal Crossing, the American release (GAFE01,
  revision 0), as a plain `.iso`.
- Optionally the AF Project's patch, `NAFE-WIP-2_12_2010.ups`: its English
  menu labels, its title logo and 96 of its messages are used if you have
  it. Without it those stay the cartridge's.

Nothing of Nintendo's is in this repository, and no ROM or patch is
distributed here: see [NOTICE.md](NOTICE.md).

## Building it

On Ubuntu or Debian:

```sh
sudo apt install make git build-essential clang binutils-mips-linux-gnu \
    python3 python3-venv cmake nasm libsdl2-dev libpng-dev zlib1g-dev

make ROM=path/to/your/dump          # rebuilds the cartridge and verifies it
make script ISO=path/to/disc.iso    # reads the official script from your disc
make nafe NAFE_UPS=path/to/NAFE-WIP-2_12_2010.ups    # optional
make rom-en                         # build/animalforest-en.z64
```

With the three inputs above, version 1.0 comes out as MD5
`52c6b4fbadb03fc9dc6526190fdb1b30` (24 MiB) on the machine it was made on.

```sh
make test          # the tools' own tests (no ROM needed; this is what CI runs)
make emu           # the headless emulator the checks use
make emu-check     # boots the rebuilt cartridge in it
make emu-check-en  # boots the English ROM
```

There are some two dozen more checks, each of which plays a part of the game
in the emulator and measures what it sees (`make messages-check-en`,
`year-check-en`, `trip-check-en`, ...): [README.es.md](README.es.md) lists
them, and [CLAUDE.md](CLAUDE.md) says which one a change calls for.

## Patches

`make bps` writes `build/animalforest-en.bps`, the English ROM as a BPS
patch against your dump. It carries, in the clear, what the build took from
your disc and from the 2010 patch: it is for your own use.

`make dist NAFE_UPS=...` writes the release's files into `build/dist`: the
same `.bps` under the version's name, a **sealed patch** (`.afp`) and a
manifest of sizes and hashes. A sealed patch is the `.bps` with every byte
crossed with a keystream drawn from the bytes of the disc's own files and of
the 2010 patch. No password opens it; the files do. It gives the ROM to
someone who has the dump, the same disc and the same patch, and nothing to
anyone else:

```sh
python3 tools/af_patch.py apply your-dump.z64 animalforest-en-v1.0.afp out.z64 \
    --iso your-disc.iso --ups NAFE-WIP-2_12_2010.ups
```

This needs Python 3 and this repository's `tools/` only: no compiler, on any
system. The patcher checks every input by its hash before it opens anything,
and the ROM it makes against the one the patch was sealed for.

A sealed patch is still a copy of that material, under a seal. Whether to
pass one on is for whoever made it to decide.

## Playing it

- The save is the cartridge's: 128 KB of Flash RAM, the real-time clock, and
  a Controller Pak for trips. The ROM keeps the cartridge's ID (NAFJ), so an
  emulator or a flash cartridge that knows the game by its ID sets these by
  itself.
- Played here on mupen64plus (with angrylion's renderer), ares, Project64,
  RetroArch (Mupen64Plus-Next), RMG and simple64: NOTES, "Other emulators",
  says what each needs.
- A save made on the English ROM belongs to it. The same Controller Pak
  travels between the English ROM and the Japanese cartridge in both
  directions.

## How it is checked

Every claim about the game is checked against the ROM, the decompiled code
or the running game, and its source is cited beside it in
[reference/NOTES.md](reference/NOTES.md). The emulator the checks use is
deterministic on purpose (fixed clock, fixed noise, one render thread), so a
check that passes once passes again. The checks hold, among other things:
every message that can be shown without a choice, shown and measured; a
year's 21 dates, each with its event's characters talked to; a first hour of
a new game played with the pad; a trip with a Controller Pak to a second
town and back; the free memory in a full town on every date.

## Where things are

- `Makefile` — everything above.
- `decomp/` — the pinned commit of zeldaret/af, `matching.patch`
  (decompiled code that still rebuilds the cartridge) and `changes.patch`
  (the translation, on top).
- `script/` — this project's own English.
- `tools/` — the build's tools: text, font, names, signs, the relink, the
  patches.
- `emu/`, `tests/` — the headless emulators' frontends and the checks.
- `reference/NOTES.md` — what has been verified, and how.

## Credits

- [zeldaret/af](https://github.com/zeldaret/af), the decompilation this is
  built on, and [ACreTeam/ac-decomp](https://github.com/ACreTeam/ac-decomp),
  the GameCube's, read as a map.
- The AF Project (Zoinkity), whose 2010 patch showed what an English Animal
  Forest could be, and whose labels, logo and messages the build can use.
- mupen64plus, angrylion-rdp-plus and ares, the emulators the checks run on.
- Nintendo, whose game this is, and whose English most of the text is.

The code, the translation and the notes were written with an AI model
(Claude, by Anthropic) working under the direction of the repository's
owner.

## License

MIT for what this project wrote; the patches to the decomp are also CC0.
[NOTICE.md](NOTICE.md) says what that covers and what it does not.
