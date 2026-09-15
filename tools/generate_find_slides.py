from __future__ import annotations

import argparse
import itertools
import random
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from lxml import html
from PIL import Image, ImageDraw, ImageFilter, ImageFont


CANVAS_SIZE = (2000, 3555)
PRODUCT_ZONE = (130, 250, 1870, 2270)
TEXT_ZONE = (150, 2440, 1850, 3260)
FONT_PATH = Path(r"C:\Windows\Fonts\times.ttf")


@dataclass(frozen=True)
class Product:
    name: str
    image_path: Path
    link: str
    width: int
    height: int
    white_ratio: float


def clean_name(raw_name: str) -> str:
    name = re.sub(r"^\s*\[(?:BEST|BUDGET)\]\s*", "", raw_name, flags=re.I)
    name = re.sub(r"^\s*BEST\s+BATCH\s+", "", name, flags=re.I)
    name = re.sub(r"\s*\((?:budget|limited stock)\)\s*$", "", name, flags=re.I)
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", name)
    name = re.sub(r"(?<=[A-Za-z0-9])(?=\()", " ", name)
    name = re.sub(r'^(\S+)"', r'\1 "', name)
    name = re.sub(r'("[A-Za-z ]+")(?=[A-Za-z])', r'\1 ', name)

    name = re.sub(
        r"\s*Ã[^0-9]*(\d+\+\s+colors)Ã.*$",
        r" (\1)",
        name,
        flags=re.I,
    )

    spacing_fixes = {
        "Jumbolace": "Jumbo Lace",
        "No faithstudios": "No faith studios",
        "Nofaithstudios": "No faith studios",
        "Zipup": "Zip Up",
        "Tshirt": "T Shirt",
        "Z Ip": "Zip",
    }
    for old, new in spacing_fixes.items():
        name = re.sub(rf"\b{re.escape(old)}\b", new, name, flags=re.I)

    return re.sub(r"\s+", " ", name).strip()


def parse_products(
    index_path: Path,
    min_side: int = 600,
    min_long_side: int = 800,
    min_white_ratio: float = 0.30,
    min_occupied: float = 0.12,
) -> list[Product]:
    document = html.parse(str(index_path))
    products: list[Product] = []

    for row in document.xpath("//tbody/tr"):
        cells = row.xpath("./td")
        image_sources = row.xpath(".//img/@src")
        if len(cells) < 5 or not image_sources:
            continue

        raw_name = " ".join(" ".join(cells[2].itertext()).split())
        image_path = index_path.parent / image_sources[0]
        links = cells[4].xpath(".//a/@href")
        if not raw_name or not image_path.exists():
            continue

        try:
            with Image.open(image_path) as image:
                width, height = image.size
                if min(width, height) < min_side or max(width, height) < min_long_side:
                    continue

                preview = image.convert("RGB")
                preview.thumbnail((240, 240), Image.Resampling.LANCZOS)
                pixels = np.asarray(preview)
                white_ratio = float(np.all(pixels > 238, axis=2).mean())
                foreground = ~np.all(pixels > 245, axis=2)
                ys, xs = np.where(foreground)
                if not len(xs):
                    continue
                occupied = (
                    (xs.max() - xs.min() + 1)
                    * (ys.max() - ys.min() + 1)
                    / (pixels.shape[0] * pixels.shape[1])
                )
                if white_ratio < min_white_ratio or occupied < min_occupied:
                    continue
        except (OSError, ValueError):
            continue

        products.append(
            Product(
                name=clean_name(raw_name),
                image_path=image_path,
                link=links[0] if links else "",
                width=width,
                height=height,
                white_ratio=white_ratio,
            )
        )

    return products


def connected_background_alpha(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    work = rgb.copy()
    marker = (1, 255, 1)
    draw = ImageDraw.Draw(work)
    width, height = work.size

    seeds = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    seeds.extend((x, 0) for x in range(0, width, max(1, width // 12)))
    seeds.extend((x, height - 1) for x in range(0, width, max(1, width // 12)))
    seeds.extend((0, y) for y in range(0, height, max(1, height // 12)))
    seeds.extend((width - 1, y) for y in range(0, height, max(1, height // 12)))

    for seed in seeds:
        current = work.getpixel(seed)
        if current == marker or min(current) < 205:
            continue
        ImageDraw.floodfill(work, seed, marker, thresh=42)

    array = np.asarray(work)
    background = np.all(array == marker, axis=2)
    alpha = Image.fromarray(np.where(background, 0, 255).astype(np.uint8), mode="L")
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.75))

    rgba = image.convert("RGBA")
    rgb_array = np.asarray(rgba.convert("RGB"), dtype=np.float32)
    alpha_array = np.asarray(alpha, dtype=np.float32) / 255.0
    safe_alpha = np.maximum(alpha_array[:, :, None], 0.08)
    clean_rgb = 255.0 - (255.0 - rgb_array) / safe_alpha
    rgba = Image.fromarray(np.clip(clean_rgb, 0, 255).astype(np.uint8), mode="RGB").convert("RGBA")
    rgba.putalpha(alpha)
    return rgba


def crop_to_subject(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    bbox = alpha.point(lambda value: 255 if value > 16 else 0).getbbox()
    if not bbox:
        return image
    padding = max(8, int(max(image.size) * 0.012))
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(image.width, bbox[2] + padding)
    bottom = min(image.height, bbox[3] + padding)
    return image.crop((left, top, right, bottom))


def place_product(canvas: Image.Image, source_path: Path) -> tuple[int, int, int, int]:
    with Image.open(source_path) as source:
        cutout = crop_to_subject(connected_background_alpha(source))

    left, top, right, bottom = PRODUCT_ZONE
    max_width = right - left
    max_height = bottom - top
    scale = min(max_width / cutout.width, max_height / cutout.height)
    target_size = (
        max(1, round(cutout.width * scale)),
        max(1, round(cutout.height * scale)),
    )
    cutout = cutout.resize(target_size, Image.Resampling.LANCZOS)

    x = (canvas.width - cutout.width) // 2
    y = top + (max_height - cutout.height) // 2
    alpha = cutout.getchannel("A")

    cast_mask = Image.new("L", canvas.size, 0)
    cast_mask.paste(alpha, (x + 50, y + 64))
    cast_mask = cast_mask.filter(ImageFilter.GaussianBlur(22))
    cast_mask = cast_mask.point(lambda value: round(value * 0.27))
    cast_shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    cast_shadow.putalpha(cast_mask)

    contact_mask = Image.new("L", canvas.size, 0)
    contact_mask.paste(alpha, (x + 14, y + 22))
    contact_mask = contact_mask.filter(ImageFilter.GaussianBlur(6))
    contact_mask = contact_mask.point(lambda value: round(value * 0.12))
    contact_shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    contact_shadow.putalpha(contact_mask)

    canvas.alpha_composite(cast_shadow)
    canvas.alpha_composite(contact_shadow)
    canvas.alpha_composite(cutout, (x, y))
    return x, y, cutout.width, cutout.height


def line_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def balanced_lines(
    draw: ImageDraw.ImageDraw,
    name: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    line_counts: tuple[int, ...],
) -> list[str] | None:
    words = name.split()
    best: tuple[float, list[str]] | None = None
    for line_count in line_counts:
        if line_count < 1 or line_count > len(words):
            continue
        for breaks in itertools.combinations(range(1, len(words)), line_count - 1):
            points = (0, *breaks, len(words))
            lines = [" ".join(words[points[i] : points[i + 1]]) for i in range(line_count)]
            widths = [line_width(draw, line, font) for line in lines]
            if max(widths) > max_width:
                continue
            raggedness = (max(widths) - min(widths)) ** 2 if len(widths) > 1 else 0
            score = max(widths) + raggedness / max_width
            if best is None or score < best[0]:
                best = (score, lines)
    return best[1] if best else None


def draw_product_name(canvas: Image.Image, name: str) -> list[str]:
    draw = ImageDraw.Draw(canvas)
    left, top, right, bottom = TEXT_ZONE
    max_width = right - left
    selected_font: ImageFont.FreeTypeFont | None = None
    selected_lines: list[str] | None = None

    preferred_counts = (1,) if len(name.split()) == 1 else (2,)
    for font_size in range(205, 144, -5):
        font = ImageFont.truetype(str(FONT_PATH), font_size)
        lines = balanced_lines(draw, name, font, max_width, preferred_counts)
        if lines is not None:
            selected_font, selected_lines = font, lines
            break

    if selected_lines is None:
        for font_size in range(205, 119, -5):
            font = ImageFont.truetype(str(FONT_PATH), font_size)
            lines = balanced_lines(draw, name, font, max_width, (3,))
            if lines is not None:
                selected_font, selected_lines = font, lines
                break

    if selected_font is None or selected_lines is None:
        selected_font = ImageFont.truetype(str(FONT_PATH), 120)
        selected_lines = [name]

    spacing = max(22, round(selected_font.size * 0.20))
    metrics = [draw.textbbox((0, 0), line, font=selected_font) for line in selected_lines]
    line_heights = [box[3] - box[1] for box in metrics]
    total_height = sum(line_heights) + spacing * (len(selected_lines) - 1)
    y = top + (bottom - top - total_height) // 2

    shadow_layer = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    positions: list[tuple[int, int, str]] = []
    for line, box, line_height in zip(selected_lines, metrics, line_heights):
        width = box[2] - box[0]
        x = (canvas.width - width) // 2
        positions.append((x, y - box[1], line))
        shadow_draw.text((x + 13, y - box[1] + 16), line, font=selected_font, fill=(0, 0, 0, 115))
        y += line_height + spacing

    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(11))
    canvas.alpha_composite(shadow_layer)
    final_draw = ImageDraw.Draw(canvas)
    for x, baseline_y, line in positions:
        final_draw.text((x, baseline_y), line, font=selected_font, fill=(0, 0, 0, 255))

    return selected_lines


def safe_filename(index: int, name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-")
    return f"{index:02d}_{slug}.png"


def generate_slide(product: Product, output_path: Path) -> None:
    canvas = Image.new("RGBA", CANVAS_SIZE, (255, 255, 255, 255))
    place_product(canvas, product.image_path)
    draw_product_name(canvas, product.name)
    canvas.convert("RGB").save(output_path, quality=96, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate product-find slides from index.html")
    parser.add_argument("--index", type=Path, default=Path("index.html"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--names", nargs="*", default=None)
    parser.add_argument("--names-file", type=Path, default=None)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--min-side", type=int, default=600)
    parser.add_argument("--min-long-side", type=int, default=800)
    parser.add_argument("--min-white-ratio", type=float, default=0.30)
    parser.add_argument("--min-occupied", type=float, default=0.12)
    args = parser.parse_args()

    products = parse_products(
        args.index.resolve(),
        min_side=args.min_side,
        min_long_side=args.min_long_side,
        min_white_ratio=args.min_white_ratio,
        min_occupied=args.min_occupied,
    )
    if len(products) < args.count:
        raise SystemExit(f"Only {len(products)} quality-filtered products found")

    requested_names = list(args.names or [])
    if args.names_file:
        requested_names.extend(
            line.strip()
            for line in args.names_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    if requested_names:
        by_name: dict[str, Product] = {}
        for product in products:
            by_name.setdefault(product.name.casefold(), product)
        missing = [name for name in requested_names if clean_name(name).casefold() not in by_name]
        if missing:
            raise SystemExit(f"Products not found: {', '.join(missing)}")
        chosen = [by_name[clean_name(name).casefold()] for name in requested_names]
    else:
        rng = random.Random(args.seed)
        chosen = products[:]
        rng.shuffle(chosen)
        chosen = chosen[: args.count]

    args.output.mkdir(parents=True, exist_ok=True)
    for index, product in enumerate(chosen, start=args.start_index):
        output_path = args.output / safe_filename(index, product.name)
        generate_slide(product, output_path)
        print(f"{index}: {product.name} | {product.image_path.name} | {product.link}")


if __name__ == "__main__":
    main()
