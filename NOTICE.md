# What the license covers, and what it does not

`LICENSE` (MIT) covers what this project wrote: the tools (`tools/`,
`tests/`, the `Makefile`, the frontends and scripts under `emu/`), the
English text under `script/`, and the documents.

**The patches to the decomp** (`decomp/matching.patch`,
`decomp/changes.patch`) are changes to
[zeldaret/af](https://github.com/zeldaret/af), which is CC0. They are
offered under CC0 1.0 as well as under MIT, so that the decomp, or anyone,
can take any part of them with no condition at all.

**The patches to the emulators** (`emu/patches/`, `emu/ares/*.patch`) are
changes to mupen64plus-core, angrylion-rdp-plus and ares. Each is offered
under the license of the project it changes.

**Nothing of Nintendo's is in this repository**: no ROM, no disc image, no
text, graphics or audio taken from either game, no screenshots. Doubutsu no
Mori, Animal Forest and Animal Crossing are Nintendo's. This project is not
affiliated with Nintendo nor endorsed by it. The build reads the user's own
dump of the cartridge and the user's own disc of Animal Crossing (GAFE01) on
the user's machine; the ROM and the patches it produces hold Nintendo's work
beside ours, are not covered by this license, and are not distributed here.

**The AF Project's 2010 patch** (Zoinkity) is not in this repository
either. Where the build uses it (42 menu labels, the title's logo, 96
messages), it reads the user's own copy.

The commits were written with an AI model (Claude, by Anthropic) working at
the direction of the repository's owner, who holds the copyright the license
names.
