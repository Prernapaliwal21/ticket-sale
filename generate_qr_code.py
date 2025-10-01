#!/usr/bin/env python3
"""
generate_qr.py

Generate a QR code that opens a website and save it as PNG.

Dependencies:
    pip install qrcode pillow

Usage examples:
    python generate_qr.py --url "https://example.com" --out myqr.png
    python generate_qr.py --url "https://example.com" --out myqr.png --box-size 10 --border 4
    python generate_qr.py --url "https://example.com" --out myqr_with_logo.png --logo ./static/logo.png --logo-scale 4
"""

import argparse
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from PIL import Image
import os
import sys

ERROR_MAP = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


def generate_qr_png(url: str, out_path: str, box_size: int = 10, border: int = 4, error_level: str = "M", logo_path: str = None, logo_scale: int = 4):
    """
    Generate QR code PNG.

    :param url: URL to encode (when scanned, device opens this URL)
    :param out_path: output PNG file path
    :param box_size: size of each QR box (pixel)
    :param border: border boxes count
    :param error_level: one of 'L','M','Q','H' (higher = more redundancy, needed if overlaying a logo)
    :param logo_path: optional path to a logo image (will be placed centered)
    :param logo_scale: how many QR boxes across the logo will take (approx). Higher -> smaller logo.
    """
    if error_level not in ERROR_MAP:
        raise ValueError("error_level must be one of 'L','M','Q','H'")

    qr = qrcode.QRCode(
        version=None,  # automatic
        error_correction=ERROR_MAP[error_level],
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    if logo_path:
        if not os.path.isfile(logo_path):
            raise FileNotFoundError(f"Logo not found: {logo_path}")
        logo = Image.open(logo_path).convert("RGBA")

        # compute logo size: we take the QR matrix size (in pixels) and divide by logo_scale
        qr_size_px = img.size[0]  # QR is square
        # target logo width = qr_size_px / logo_scale (rounded)
        target_logo_w = max(20, qr_size_px // logo_scale)
        # keep aspect ratio
        logo_w, logo_h = logo.size
        aspect = logo_h / logo_w
        target_logo_h = int(target_logo_w * aspect)
        logo = logo.resize((target_logo_w, target_logo_h), Image.LANCZOS)

        # compute position to paste
        pos = ((qr_size_px - target_logo_w) // 2, (qr_size_px - target_logo_h) // 2)

        # create a copy and paste logo with alpha mask if present
        img_with_logo = img.copy()
        if logo.mode in ("RGBA", "LA") or (hasattr(logo, "getchannel") and "A" in logo.getbands()):
            img_with_logo.paste(logo, pos, logo)
        else:
            img_with_logo.paste(logo, pos)

        img = img_with_logo

    # ensure output directory exists
    out_dir = os.path.dirname(os.path.abspath(out_path)) or "."
    os.makedirs(out_dir, exist_ok=True)
    img.save(out_path, format="PNG")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate QR code PNG that opens a URL when scanned.")
    parser.add_argument("--url", "-u", required=True, help="URL to encode in the QR code (e.g. https://example.com)")
    parser.add_argument("--out", "-o", default="qr.png", help="Output PNG filename (default: qr.png)")
    parser.add_argument("--box-size", type=int, default=10, help="Box size in pixels for QR (default 10)")
    parser.add_argument("--border", type=int, default=4, help="Border (boxes) around QR (default 4)")
    parser.add_argument("--error-level", choices=["L", "M", "Q", "H"], default="M", help="Error correction level. Use H if adding a logo (default M)")
    parser.add_argument("--logo", "-l", help="Optional logo image path to embed in center (PNG/JPG). Use higher error-level (Q/H).")
    parser.add_argument("--logo-scale", type=int, default=4, help="Approx: how many times smaller than QR the logo should be (default 4). Larger -> smaller logo.")
    args = parser.parse_args()

    try:
        out_file = generate_qr_png(
            url=args.url,
            out_path=args.out,
            box_size=args.box_size,
            border=args.border,
            error_level=args.error_level,
            logo_path=args.logo,
            logo_scale=args.logo_scale,
        )
        print(f"QR saved to: {out_file}")
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
