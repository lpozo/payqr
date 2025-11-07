import argparse
import os

from payqr.qr import QRCodeGenerator
from payqr.templates import TemplateManager


def resolve_default_template() -> str:
    # Go up two levels from payqr package to get project root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    # Default to the 'nezaposlenost' template as discussed
    template_path = os.path.join(base_dir, "templates", "nezaposlenost.toml")
    return os.path.abspath(template_path)


def run_cli(template_path: str, out_path: str) -> None:
    tm = TemplateManager(template_path)
    payload = tm.render_payload()
    QRCodeGenerator().generate_and_save(payload, out_path)
    print(f"Saved QR to {out_path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="PayQR - QR Code Generator (CLI)")
    parser.add_argument(
        "--template", default=resolve_default_template(), help="Path to TOML template"
    )
    parser.add_argument("--out", required=True, help="Write PNG to this path")
    args = parser.parse_args(argv)

    run_cli(args.template, args.out)


if __name__ == "__main__":
    main()
