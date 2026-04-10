# Generic IR Fan Home Assistant Integration

Control any IR fan with any Home Assistant-compatible remote (Broadlink, Tuya, etc.) by "teaching" the integration your IR codes.

## Features

- Adds a `fan` entity and its own **device** in Home Assistant.
- Compatible with any Home Assistant `remote` integration.
- Lets you select the IR remote from a **dropdown** during setup.
- Configure the **number of fan speeds** during setup.
- Supports both direct speed commands (`speed_1`, `speed_2`, etc.) and a single `speed_toggle` command that cycles through speeds.
- Adds GUI helpers to learn commands directly from the device page using a select entity and buttons.
- Supports fans that **do not** have a dedicated `on` command by turning on with a default speed instead.
- Can link to an optional **power monitor** to detect on/off and infer the current speed from wattage.

## Installation

### HACS

1. In HACS, add `https://github.com/sambtc94/ha_generic_ir_fan` as a **custom repository** of type **Integration**.
2. Install the latest version from HACS.
3. Restart Home Assistant.
4. Add the integration via **Settings > Devices & Services > Add Integration > Generic IR Fan**.

### Manual

1. Copy this folder to `/custom_components/ha_generic_ir_fan/` in your Home Assistant config.
2. Restart Home Assistant.
3. Add the integration via **Settings > Devices & Services > Add Integration > Generic IR Fan**.
4. Select the IR remote, configure the speed count, and optionally link a power sensor plus per-speed watt values.
5. Open the device page and use the **IR action** select plus the **Learn selected command** button to teach commands.

## Learning command names

You can learn commands from the GUI or via the `learn_command` service using these action names:

- `on` *(optional if your fan needs a separate on command)*
- `off`
- `speed_1` through your configured max speed
- `speed_toggle` *(for fans with a single speed-cycle button)*
- `oscillate`
- `mode_<name>` for each preset mode, for example `mode_sleep` or `mode_natural`

If your fan has **no** dedicated on button, leave that option disabled and the entity will use the configured default speed when you turn it on.

If you link a power sensor, you can also provide comma-separated per-speed watt values such as `8, 14, 21` so the integration can better infer the current speed when the fan is turned on outside Home Assistant.

## License

MIT License - see [LICENSE](LICENSE)

---