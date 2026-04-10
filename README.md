# Generic IR Fan Home Assistant Integration

Control any IR fan with any Home Assistant-compatible remote (Broadlink, Tuya, etc.) by "teaching" the integration your IR codes.

## Features

- Adds a `fan` entity to Home Assistant for your IR remote fan.
- Compatible with any Home Assistant `remote` integration.
- Learn and use IR commands for `off`, `speed_1`-`speed_3`, oscillate, and optional preset modes.
- Supports fans that **do not** have a dedicated `on` command by turning on with a default speed instead.
- UI setup (config flow).
- Entity services for learning and clearing IR codes.

## Installation

1. Copy this folder to `/custom_components/ha_generic_ir_fan/` in your Home Assistant config.
2. Restart Home Assistant.
3. Add the integration via **Settings > Devices & Services > Add Integration > Generic IR Fan**.
4. Select your IR remote entity, choose whether the fan has a dedicated `on` command, and optionally add preset modes like `normal, natural, sleep`.
5. Use the fan entity services to learn each action you want to support.

## Learning command names

Use the fan entity's `learn_command` service with these action names:

- `on` *(optional if your fan needs a separate on command)*
- `off`
- `speed_1`
- `speed_2`
- `speed_3`
- `oscillate`
- `mode_<name>` for each preset mode, for example `mode_sleep` or `mode_natural`

If your fan has **no** dedicated on button, leave that option disabled and the entity will use the configured default speed when you turn it on.

## License

MIT License - see [LICENSE](LICENSE)

---