#!/usr/bin/env python3
"""
Read-only backup of a ZMK keymap via the ZMK Studio protocol.

It ONLY reads from the keyboard. It never calls set/save/discard/reset.

Setup:
    pip install zmk-studio-api            (Windows: py -m pip install zmk-studio-api)

Usage:
    python zmk_backup.py                  auto-detect USB serial port
    python zmk_backup.py --port COM5      explicit port (Windows)
    python zmk_backup.py --port /dev/cu.usbmodem1101   (macOS)
    python zmk_backup.py --ble            over Bluetooth instead of USB

Close ZMK Studio (browser tab / desktop app) first: only one program can
hold the serial port at a time.
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import sys
import time
from datetime import datetime

try:
    import zmk_studio_api as zmk
except ImportError:
    sys.exit("Missing dependency. Run:  pip install zmk-studio-api")


# ---------------------------------------------------------------- protobuf ---
# Tiny protobuf wire-format reader, so no extra dependencies are needed.

def _varint(buf: bytes, i: int) -> tuple[int, int]:
    shift = result = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, i
        shift += 7


def _fields(buf: bytes):
    """Yield (field_number, wire_type, value) for each field in a message."""
    i = 0
    while i < len(buf):
        key, i = _varint(buf, i)
        num, wt = key >> 3, key & 7
        if wt == 0:
            val, i = _varint(buf, i)
        elif wt == 2:
            ln, i = _varint(buf, i)
            val, i = buf[i:i + ln], i + ln
        elif wt == 5:
            val, i = int.from_bytes(buf[i:i + 4], "little"), i + 4
        elif wt == 1:
            val, i = int.from_bytes(buf[i:i + 8], "little"), i + 8
        else:
            raise ValueError(f"unsupported wire type {wt}")
        yield num, wt, val


def _zigzag(n: int) -> int:
    return (n >> 1) ^ -(n & 1)


def decode_binding(buf: bytes) -> dict:
    out = {"behavior_id": 0, "param1": 0, "param2": 0}
    for num, _, val in _fields(buf):
        if num == 1:
            out["behavior_id"] = _zigzag(val)
        elif num == 2:
            out["param1"] = val
        elif num == 3:
            out["param2"] = val
    return out


def decode_layer(buf: bytes) -> dict:
    out = {"id": 0, "name": "", "bindings": []}
    for num, _, val in _fields(buf):
        if num == 1:
            out["id"] = val
        elif num == 2:
            out["name"] = val.decode("utf-8", "replace")
        elif num == 3:
            out["bindings"].append(decode_binding(val))
    return out


def decode_keymap(buf: bytes) -> dict:
    out = {"layers": [], "available_layers": 0, "max_layer_name_length": 0}
    for num, _, val in _fields(buf):
        if num == 1:
            out["layers"].append(decode_layer(val))
        elif num == 2:
            out["available_layers"] = val
        elif num == 3:
            out["max_layer_name_length"] = val
    return out


def decode_name_field(buf: bytes, field: int = 2) -> str:
    for num, wt, val in _fields(buf):
        if num == field and wt == 2:
            return val.decode("utf-8", "replace")
    return ""


# ------------------------------------------------------------- connection ---

def find_serial_port() -> str | None:
    try:
        from serial.tools import list_ports  # optional (pyserial)
        ports = [p.device for p in list_ports.comports()
                 if "usbmodem" in p.device or "ACM" in p.device
                 or (p.vid is not None)]
        if len(ports) == 1:
            return ports[0]
        if ports:
            print("Several serial ports found:", ", ".join(ports))
            return None
    except ImportError:
        pass
    cands = glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/ttyACM*")
    if len(cands) == 1:
        return cands[0]
    if cands:
        print("Several serial ports found:", ", ".join(cands))
    return None


def connect(args) -> "zmk.StudioClient":
    if args.ble:
        print("Scanning for Bluetooth keyboards...")
        devices = zmk.StudioClient.list_ble_devices()
        if not devices:
            sys.exit("No Bluetooth keyboards found. Is the keyboard connected to this computer?")
        for n, (dev_id, name) in enumerate(devices):
            print(f"  [{n}] {name or '(no name)'}  {dev_id}")
        pick = 0
        if len(devices) > 1:
            pick = int(input("Which one? ") or "0")
        return zmk.StudioClient.open_ble(devices[pick][0])

    port = args.port or find_serial_port()
    if not port:
        sys.exit("Could not pick a serial port automatically. Re-run with --port "
                 "(e.g. --port COM5 on Windows, --port /dev/cu.usbmodemXXXX on macOS).")
    print(f"Opening {port} ...")
    return zmk.StudioClient.open_serial(port)


def wait_for_unlock(client) -> None:
    state = client.get_lock_state()
    if "UNLOCKED" in state:
        return
    print("\nKeyboard is LOCKED. Press the Studio Unlock key now")
    print("(on the stock TOTEM layout: hold SPACE, then ENTER, then tap Z).")
    for _ in range(120):
        time.sleep(1)
        if "UNLOCKED" in client.get_lock_state():
            print("Unlocked.\n")
            return
    sys.exit("Timed out waiting for unlock.")


# ------------------------------------------------------------------ main ---

TOTEM_ROWS = [10, 10, 12, 6]   # TOTEM has 38 keys


def grid(labels: list[str]) -> str:
    if len(labels) != sum(TOTEM_ROWS):
        return "\n".join(f"  [{i:2}] {l}" for i, l in enumerate(labels))
    lines, i = [], 0
    for row in TOTEM_ROWS:
        chunk = labels[i:i + row]
        lines.append("  " + " | ".join(f"[{i + k:2}] {c}" for k, c in enumerate(chunk)))
        i += row
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only ZMK Studio keymap backup")
    ap.add_argument("--port", help="serial port (COMx, /dev/cu.usbmodemXXXX, /dev/ttyACMx)")
    ap.add_argument("--ble", action="store_true", help="connect over Bluetooth instead of USB")
    args = ap.parse_args()

    client = connect(args)
    info_raw = bytes(client.get_device_info_bytes())
    device_name = decode_name_field(info_raw, field=1)
    print("Connected to:", device_name or "(unknown)")

    wait_for_unlock(client)

    print("Reading behaviors...")
    behaviors = {}
    for bid in client.list_all_behaviors():
        raw = bytes(client.get_behavior_details_bytes(bid))
        behaviors[bid] = {"name": decode_name_field(raw, field=2),
                          "details_b64": base64.b64encode(raw).decode()}

    print("Reading keymap...")
    keymap_raw = bytes(client.get_keymap_bytes())
    keymap = decode_keymap(keymap_raw)
    layouts_raw = bytes(client.get_physical_layouts_bytes())

    txt = [f"ZMK keymap backup of {device_name}  —  {datetime.now():%Y-%m-%d %H:%M}", ""]
    for li, layer in enumerate(keymap["layers"]):
        name = layer["name"] or f"layer {li}"
        print(f"  layer {li}: {name} ({len(layer['bindings'])} keys)")
        labels = []
        for pos, b in enumerate(layer["bindings"]):
            b["behavior"] = behaviors.get(b["behavior_id"], {}).get("name", "?")
            try:
                b["decoded"] = str(client.get_key_at(layer["id"], pos))
            except Exception as e:  # keep going, raw data is still saved
                b["decoded"] = f"<error: {e}>"
            labels.append(b["decoded"].removeprefix("Behavior(").removesuffix(")"))
        txt += [f"=== Layer {li}: {name} (id {layer['id']}) ===", grid(labels), ""]

    stamp = f"{datetime.now():%Y%m%d-%H%M}"
    base = f"zmk-keymap-backup-{stamp}"
    backup = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "device_name": device_name,
        "keymap": keymap,
        "behaviors": {str(k): v for k, v in behaviors.items()},
        "raw_b64": {
            "keymap": base64.b64encode(keymap_raw).decode(),
            "physical_layouts": base64.b64encode(layouts_raw).decode(),
            "device_info": base64.b64encode(info_raw).decode(),
        },
    }
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=2)
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write("\n".join(txt))

    print(f"\nSaved {base}.json and {base}.txt")
    print("Nothing on the keyboard was changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
