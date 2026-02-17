# SolaX EVC Charger Integration

Tato integrace umožňuje vyčítat data z EV nabíječky SolaX (X3-EVC) přímo přes lokální síť pomocí HTTP API.

## Instalace

1. Nainstalujte tuto integraci přes HACS (přidáním jako vlastní repozitář).
2. Restartujte Home Assistant.
3. Přidejte následující konfiguraci do vašeho `configuration.yaml`:

```yaml
sensor:
  - platform: solax_evc
    host: "192.168.0.106"     # IP adresa vaší nabíječky
    password: "VASE_HESLO"    # Heslo (výchozí bývá sériové číslo Pocket WiFi)
