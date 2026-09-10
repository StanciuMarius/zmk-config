# TOTEM + nRF52840 dongle (ZMK)

ZMK config for a [TOTEM](https://github.com/GEIGEIGEIST/TOTEM) split keyboard
driven by a **Makerdiary nRF52840 MDK USB Dongle**.

The dongle stays plugged into the computer and is the BLE **central**: it holds
the keymap and speaks USB HID to the host. Both halves are BLE **peripherals**
that only ever talk to the dongle. This replaces the stock Mechboards setup,
where the left half was the central and paired to the computer directly.

## Builds

GitHub Actions builds five firmware files on every push:

| Artifact | Board | Flash it to |
|---|---|---|
| `totem_dongle-nrf52840_mdk_usb_dongle-zmk.uf2` | Makerdiary dongle | the dongle |
| `totem_left-xiao_ble-zmk.uf2` | XIAO nRF52840 | left half |
| `totem_right-xiao_ble-zmk.uf2` | XIAO nRF52840 | right half |
| `settings_reset-xiao_ble-zmk.uf2` | XIAO nRF52840 | each half, **before** the real firmware |
| `settings_reset-nrf52840_mdk_usb_dongle-zmk.uf2` | Makerdiary dongle | the dongle, **before** the real firmware |

## Flashing

Settings-reset first, on all three devices, to clear stale BLE bonds.

- **Halves** - double-tap the reset button; a USB drive appears; drop the
  `.uf2` on it.
- **Dongle** - hold the button while plugging it in. The RGB LED goes green and
  a `UF2BOOT` drive appears; drop the `.uf2` on it. The LED blinks red while
  writing. Unplug and replug.

Then remove the old "TOTEM" pairing from the computer's Bluetooth settings.

There is no `&bootloader` key bound for the dongle - use the physical button.

## Layout

38 keys, four layers: BASE, NAVI, SYM, ADJ. ADJ is reached by holding **both**
thumb SPACE keys.

The keymap in `config/totem.keymap` was recovered from the stock firmware over
ZMK Studio's RPC protocol, because Studio has no export feature
([zmk-studio#124](https://github.com/zmkfirmware/zmk-studio/issues/124)). See
[`backup/`](backup/).

ZMK Studio still works after the switch - connect to the dongle over USB. The
physical layout in `config/boards/shields/totem/totem_layout.dtsi` was decoded
from the backup, so the Studio view is unchanged.

## Rollback

Mechboards' reset file plus their stock left/right firmware from the
[TOTEM guide](https://guides-mechboards.gitbook.io/guides/getting-started/totem)
restores the original direct-Bluetooth setup. That firmware carries the *stock*
keymap, which is why `backup/` matters.
