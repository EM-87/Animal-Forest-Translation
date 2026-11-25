# For zeldaret/af: decompiled code, and what was learned on the way

This comes from [EM-87/Animal-Forest-Translation](https://github.com/EM-87/Animal-Forest-Translation),
an English translation of the game that is built on the decomp: it rebuilds the cartridge from
zeldaret/af, moves the code where it can grow, and changes it from there. To do that, some of the game
had to be read closely enough to turn it into C. That C is of no use to the translation alone, so here
it is, with the tools and the notes that came with it.

Nobody asked for this. Take all of it, a part, or none.

**License.** Everything in this package is offered under CC0 1.0, as the decomp is.

**How it was written.** By an AI model (Claude, by Anthropic), driven by the repository's owner over
several weeks. Nothing in it was taken on trust: a function is here because the ROM built with it is the
cartridge's, byte for byte. If the project has a rule about machine-written code, this is the place to
apply it; the patch is one file, easy to refuse.

## The patch

`matching.patch` is one patch on top of commit `4ddba04604ee7b4c4cfc0b64f8ee4d094bb385be`
("Generate decomp.dev progress reports (#249)"). With it applied the build still produces the matching
ROM (the repository's `checksum.md5`; the dump's MD5 is `a4f7c57c180297b2e7ba5a5feb44fe0b`), which
the translation's own build checks every time (`make verify`). It has not been rebased: the package was
put together where the decomp's repository could not be fetched, so the head may have moved under it.

It touches 28 files. In the 16 C files (counted with a simple pattern, so take the figures as near):

| file | C, matching | C, not matching | left in asm | what it is |
| --- | ---: | ---: | ---: | --- |
| `src/code/m_flashrom.c` | 35 | 6 | 1 | the flash save: its slots, checksums and the letters' stores |
| `src/code/m_font.c` | 6 | 0 | 56 | the font: a character's width and drawing |
| `src/code/m_handbill.c` | 41 | 0 | 7 | the letters: their banks, loaders and free strings |
| `src/code/m_item_name.c` | 1 | 1 | 0 | an item's name copied |
| `src/code/m_msg_main.c` | 278 | 4 | 0 | the message system: the window, its codes, the pages, the talk orders |
| `src/code/m_museum.c` | 0 | 0 | 39 | split out as a file of its own (all still asm) |
| `src/code/m_notice.c` | 4 | 0 | 9 | the bulletin board's posts |
| `src/overlays/actors/ovl_Animal_Logo/ac_animal_logo.c` | 2 | 0 | 31 | the title's logo: its pieces drawn, the no-controller warning |
| `src/overlays/actors/ovl_Npc_Police/ac_npc_police.c` | 1 | 0 | 25 | one function of the policeman's |
| `src/overlays/submenu/board_ovl/m_board_ovl.c` | 4 | 2 | 16 | the letter board: lines, pages, the finish |
| `src/overlays/submenu/ledit_ovl/m_ledit_ovl.c` | 0 | 0 | 10 | the name entry: its table of windows (data) |
| `src/overlays/submenu/ovl__0078CB80/ovl__0078CB80.c` | 10 | 0 | 45 | the editor: the cursor, line breaks, the field switch |
| `src/overlays/submenu/ovl__00792700/ovl__00792700.c` | 1 | 0 | 26 | a menu's strings |
| `src/overlays/submenu/ovl__00797A50/ovl__00797A50.c` | 1 | 1 | 24 | the bulletin board's menu |
| `src/overlays/submenu/ovl__00799580/ovl__00799580.c` | 1 | 0 | 13 | the edit-end check's question |
| `src/overlays/submenu/tag_ovl/m_tag_ovl.c` | 0 | 1 | 135 | the tag over an item: one function (its frame is too large by a local) |
| **all** | **385** | **15** | **437** | |

- **`m_msg_main.c` is whole**: every function of the message system is in C, four of them behind
  `NON_MATCHING`. The header `include/m_msg_main.h` has the window's layout as the code uses it.
- **C that does not match** is kept behind `#ifdef NON_MATCHING`, with the original's `GLOBAL_ASM` in
  the `#else`: the default build is the matching one.
- **The other 12 files** are headers (`include/m_msg_main.h`, `m_flashrom.h`, `m_clip.h`,
  `m_common_data.h`, `6B3DC0.h`, two actors'), the two yamls (segments split into C files),
  `linker_scripts/jp/symbol_addrs_overlays.txt` and `undefined_syms.ld`, and
  `relocs/reloc_addrs-jp.txt` (below).
- **No data from the ROM is in the patch.** Three of the submenu overlays have tables of the
  cartridge's text in their data. The patch includes them from generated files
  (`assets/jp/overlays/submenu/.../*.inc.c`), which `tools/af_dumpdata.py` writes from the user's ROM
  after the extract. The decomp will have its own way to hold such data; the tool shows where it is.

## What was learned (notes/)

`notes/` has the sections of the translation's notes that are about the decomp, each claim with its
source. The ones that cost the most to find:

- **An address spelled with the wrong symbol still matches.** IDO folds a constant index into a
  table's address (`table[name - 0x8000]` becomes `table - 0x10000`), and the disassembler names that
  address after whatever symbol lies there, inside some unrelated function. The bytes are right until
  anything moves. `tools/af_anchors.py` finds the class; the fixes are entries in
  `relocs/reloc_addrs-jp.txt` (`addend:-0x10000`).
- **The cartridge's own files hold RAM addresses.** 2,348 texture loads in the field models name
  buffers in code's bss by address. Assets are not linked, so nothing in code may move in RAM; the
  translation moves code in ROM only (`tools/af_relink.py`, `af_relsyms.py`).
- **A shared header can reorder another file's bss** under IDO; a new type is best kept in the file
  that needs it.
- **Under `-g3` every declared local has a home in the frame**, used or not. A function whose
  instructions all match but whose frame is too large declares more locals than the original did.
- **A bank's table of ends is read two ends at a time**: the loaders take an even entry's ends 16
  bytes from the entry two before it, so the last entry of an odd count reads past the table.
- **The Makefile marks every target `.SECONDARY`**: after an object is built another way, deleting
  it alone rebuilds nothing while the ROM is newer than the sources.

## The tools (tools/)

They run from the translation's repository; they are here to be read, or lifted.

- `af_match.py` — one function at a time: builds its object and compares its bytes with the
  cartridge's, data references masked. `af_try.py` tries variants of a function in its file;
  `af_bench.py` sweeps many variants outside the build; `af_wrap.py` puts a function behind
  `NON_MATCHING`.
- `af_anchors.py`, `af_luicheck.py`, `af_shiftcheck.py` — the proofs the translation's build runs
  before it lets code move: no address spelled with the wrong symbol, no shared `lui` broken,
  nothing of the cartridge's moved in RAM.
- `af_relink.py`, `af_relsyms.py`, `af_ranges.py`, `af_dmaorder.py`, `af_ovlreloc.py` — a build in
  which `code` lies at the end of the ROM and may grow: the linker script rewritten, the absolute
  addresses made relative, the compressed ROM's ranges, an overlay's relocation table made anew.
- `af_dumpdata.py` — the cartridge's data a decompiled file needs, written from the user's ROM as C
  initializers.

The rest of the translation (the text tools, a headless and deterministic mupen64plus for checks,
some two dozen checks that play the game) is in the repository, under MIT.
