# SolaX EVC Charger Integration

Local API Polling of Solax EV Charger

## Installaton

1. Add custom integration.
2. Restart Home Assistant.
3. Add following config into `configuration.yaml`:

```yaml
sensor:
  - platform: solax_evc
    host: "192.168.0.106"     # Local IP addres of charger
    password: "PASSWORD"      # Password (use QR code on charger sticker)
