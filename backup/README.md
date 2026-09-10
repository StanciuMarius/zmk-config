# Keymap backup

The only copy of the keymap that shipped on this TOTEM, pulled off the
keyboard over the ZMK Studio RPC protocol on 2026-09-10 before anything was
reflashed. Keep it.

| File | What it is |
|---|---|
| `zmk-keymap-backup-20260910-1018.json` | Full dump: layers, bindings, behavior names, and the raw protobuf (keymap, physical layouts, device info) as base64. |
| `zmk-keymap-backup-20260910-1018.txt` | The same thing as a human-readable grid. |
| `totem-layout-check.svg` | The physical layout decoded out of the dump and rendered, used to check it was read correctly. |
| `zmk_backup.py` | The read-only script that produced the dump. |

`../config/totem.keymap` and `../config/boards/shields/totem/totem_layout.dtsi`
were both generated from the JSON.
