from __future__ import annotations

import argparse
import importlib.util
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def load_generator(path: Path):
    spec = importlib.util.spec_from_file_location("find_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=Path("index.html"))
    parser.add_argument("--generator", type=Path, default=Path("tools/generate_find_slides.py"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260901)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--min-side", type=int, default=600)
    parser.add_argument("--min-long-side", type=int, default=800)
    parser.add_argument("--min-white-ratio", type=float, default=0.30)
    parser.add_argument("--min-occupied", type=float, default=0.12)
    parser.add_argument("--exclude-names-file", type=Path, action="append", default=[])
    parser.add_argument("--skip-positions", type=int, nargs="*", default=[])
    parser.add_argument("--names-output", type=Path)
    args = parser.parse_args()

    generator = load_generator(args.generator.resolve())
    products = generator.parse_products(
        args.index.resolve(),
        min_side=args.min_side,
        min_long_side=args.min_long_side,
        min_white_ratio=args.min_white_ratio,
        min_occupied=args.min_occupied,
    )
    excluded = {
        "Christian Dior Backpack",
        "Mowalola Logo Shirt Grey",
        "Rick Owens Jumbo Lace Geobasket",
        "Balenciaga Striped Shirt",
        "Balenciaga Lost Tapes",
        "Louis Vuitton Beanie",
        "No Faith Studios Drewstring Denim",
        "Number Nine Music Coat Jacket",
        "Vetements Ecstasy Hoodie Blue",
        "LV x Timberlands",
    }
    products = [product for product in products if product.name not in excluded]
    excluded_names = {
        generator.clean_name(line.strip()).casefold()
        for path in args.exclude_names_file
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    products = [product for product in products if product.name.casefold() not in excluded_names]
    unique_products = []
    seen_names = set()
    for product in products:
        key = product.name.casefold()
        if key in seen_names:
            continue
        seen_names.add(key)
        unique_products.append(product)
    products = unique_products
    random.Random(args.seed).shuffle(products)
    products = products[args.start : args.start + args.count]
    products = [
        product
        for position, product in enumerate(products, start=1)
        if position not in set(args.skip_positions)
    ]

    if args.names_output:
        args.names_output.parent.mkdir(parents=True, exist_ok=True)
        args.names_output.write_text(
            "\n".join(product.name for product in products) + "\n",
            encoding="utf-8",
        )

    cell_size = (460, 500)
    columns = 4
    rows = (len(products) + columns - 1) // columns
    sheet = Image.new("RGB", (cell_size[0] * columns, cell_size[1] * rows), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 24)

    for index, product in enumerate(products, start=1):
        with Image.open(product.image_path) as source:
            preview = ImageOps.contain(source.convert("RGB"), (410, 380), Image.Resampling.LANCZOS)
        column = (index - 1) % columns
        row = (index - 1) // columns
        x = column * cell_size[0] + (cell_size[0] - preview.width) // 2
        y = row * cell_size[1] + 10 + (380 - preview.height) // 2
        sheet.paste(preview, (x, y))
        label = f"{index:02d}  {product.name}"
        lines = []
        words = label.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if draw.textlength(candidate, font=font) <= 420:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        draw.multiline_text(
            (column * cell_size[0] + 20, row * cell_size[1] + 405),
            "\n".join(lines[:3]),
            font=font,
            fill="black",
            spacing=3,
        )
        print(f"{index:02d}|{product.name}|{product.image_path}|{product.link}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, quality=92)


if __name__ == "__main__":
    main()
