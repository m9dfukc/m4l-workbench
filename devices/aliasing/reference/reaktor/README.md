# Reaktor source material (local only)

Everything in this folder except this README is **gitignored**: the ensemble and the screenshots
are the work of the ensemble's author and stay on the user's machine as port reference. Never
edit these files; analyses go to `devices/aliasing/docs/` and `docs/research/notes/`.

| File | Origin | Size | SHA-256 |
|---|---|---|---|
| `Aliasing Synth 515 (original 2008).ens` | Original Reaktor User Library download (file date 2008-09-18) | 144 346 | `62ec413e5947b5d54a540e101909ce2a18438ea99f3595bb75756d22311017bf` |
| `aliasing Synth.ism` | The instrument saved by the user from Reaktor 6.5.2 (2026-11-24); contains the absolute path it was saved to | 252 003 | `29977eccfad10b6b274ddd6b5b7641c6b8dec23d4d3fc097213800dfe89d146c` |
| `screenshots/` | 25 screenshots of panel and structure, taken by the user in Reaktor 6.5.2 (2026-11-24) | | |
| `description.txt` | The user's notes and links (library page, forum threads) | | |

Links:

- Reaktor User Library: https://userlibrary.native-instruments.com/reaktor/item/5241
- SuperCollider replication thread: https://scsynth.org/t/replicating-aliasing-synth-a-gem-in-reaktors-user-library/9054
- dogsonacid thread: https://www.dogsonacid.com/threads/introducing-aliasing-synth-reaktor-synth-for-sick-drones-reeses.690224/

The original 2008 ensemble is the port reference (user, 2026-11-24); the `.ism` is a Reaktor 6
re-save of its instrument, useful to compare the R6 container with the R5 stream. To restore on a new
machine: download it from the User Library and check the checksum above.
