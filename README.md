# PayQR – IPS QR Code Generator (GUI + CLI)

PayQR generates IPS payment QR codes from a TOML template. You can use a friendly Tkinter GUI or a headless CLI. Templates define the ordered key:value pairs rendered into the QR payload, joined with `|` (pipe), for example:

K:PR|V:01|C:1|R:123456789012345678|N:Recipient Name|I:RSD1000,00|P:Payment Purpose|SF:123|S:Description

## Features

- Template-driven payload (order, defaults, required fields)
- GUI with dynamic form built from the template
  - Template selector to switch between predefined templates
  - Amount field split: currency (read-only) + numeric value
  - Read-only fixed fields (IdentificationCode, Version, CodeSet)
  - Live QR preview at a fixed size
  - Auto-save protection for default template
- CLI to generate QR PNGs from templates

## Project structure

```
payqr/
├── src/
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── app.py          # GUI launcher (entry point)
│   │   ├── ui.py           # Main GUI (PayQRApp)
│   │   └── tempdlg.py      # Template dialog (unused)
│   └── payqr/
│       ├── __init__.py
│       ├── cli.py          # CLI entry point (payqr-cli)
│       ├── qr.py           # QRCodeGenerator
│       └── templates.py    # TemplateManager
├── templates/
│   ├── config.toml         # Global config (fixed fields)
│   └── default.toml        # Default template
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

## Setup

```sh
# Install dependencies (uv)
uv sync
```

## Run the GUI

```sh
uv run payqr
```

GUI highlights:

- Select a template from the dropdown menu
- Amount is entered as currency (read-only, e.g., RSD) + numeric value (e.g., 1234,56). The two are combined as `I:RSD1234,56` in the payload
- When modifying the default template, you'll be prompted to save as a new template to protect the original
- Templates are automatically saved when you generate a QR code
- Click "Generate" to create and preview the QR code, or "Save as…" to export a PNG

## Run the CLI

```sh
# Generate a QR using the default template
uv run payqr-cli --out qr.png

# Or specify a template file explicitly
uv run payqr-cli --template path/to/template.toml --out qr.png
```

## License

MIT
