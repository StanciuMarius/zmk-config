# Suppresses the duplicate unit-address warnings nRF52840 boards emit for
# power, clock, acl and flash-controller.
list(APPEND EXTRA_DTC_FLAGS "-Wno-unique_unit_address_if_enabled")
