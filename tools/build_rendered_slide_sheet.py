from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    args = parser.parse_args()

    files = []
    for path in args.input.glob("*.png"):
        try:
            number = int(path.name.split("_", 1)[0])
        except ValueError:
            continue
        if args.start <= number <= args.end:
            files.append((number, path))
    files.sort()

    tile_size = (220, 420)
    columns = 5
    rows = (len(files) + columns - 1) // columns
    sheet = Image.new("RGB", (tile_size[0] * columns, tile_size[1] * rows), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 18)

    for position, (number, path) in enumerate(files):
        with Image.open(path) as source:
            preview = source.convert("RGB")
            preview.thumbnail((210, 373), Image.Resampling.LANCZOS)
        column = position % columns
        row = position // columns
        x = column * tile_size[0] + (tile_size[0] - preview.width) // 2
        y = row * tile_size[1] + 28
        sheet.paste(preview, (x, y))
        draw.text((column * tile_size[0] + 8, row * tile_size[1] + 5), str(number), font=font, fill="black")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, quality=94)


if __name__ == "__main__":
    main()
