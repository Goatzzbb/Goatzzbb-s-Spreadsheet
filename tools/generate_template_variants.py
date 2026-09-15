from __future__ import annotations

import colorsys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


TEMPLATES_DIR = Path.home() / "Downloads" / "Templates"
REFERENCE_FILE = TEMPLATES_DIR / "05_Red_2160x3840.png"

PALETTE = [
    (31, "Burgundy", "#6D071A"),
    (32, "Wine", "#722F37"),
    (33, "Maroon", "#800000"),
    (34, "Raspberry", "#D81B60"),
    (35, "Watermelon", "#FC6C85"),
    (36, "Salmon", "#FA8072"),
    (37, "Peach", "#FFB07C"),
    (38, "Apricot", "#FBCEB1"),
    (39, "Tangerine", "#F28500"),
    (40, "Rust", "#B7410E"),
    (41, "Terracotta", "#C65D3B"),
    (42, "Mustard", "#D4A017"),
    (43, "Champagne", "#E5C07B"),
    (44, "Olive", "#808000"),
    (45, "Moss", "#6B7D3E"),
    (46, "Sage", "#87A96B"),
    (47, "Forest", "#014421"),
    (48, "Seafoam", "#4BC6A1"),
    (49, "Turquoise", "#40E0D0"),
    (50, "Aquamarine", "#7FFFD4"),
    (51, "Cerulean", "#007BA7"),
    (52, "Azure", "#007FFF"),
    (53, "Cobalt", "#0047AB"),
    (54, "Denim", "#1560BD"),
    (55, "Periwinkle", "#8E93FF"),
    (56, "Lavender", "#B57EDC"),
    (57, "Lilac", "#C8A2C8"),
    (58, "Plum", "#8E4585"),
    (59, "Orchid", "#DA70D6"),
    (60, "Mauve", "#B784A7"),
]


def hex_to_hsv(color: str) -> tuple[float, float, float]:
    color = color.lstrip("#")
    rgb = tuple(int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(*rgb)


def recolor(reference_hsv: np.ndarray, target_hex: str) -> Image.Image:
    hsv = reference_hsv.astype(np.float32)
    target_h, target_s, target_v = hex_to_hsv(target_hex)

    ref_s = 218.0 / 255.0
    ref_v = 169.0 / 255.0
    original_s = hsv[:, :, 1] / 255.0
    original_v = hsv[:, :, 2] / 255.0
    fade_weight = np.clip(original_s / ref_s, 0.0, 1.0)

    hsv[:, :, 0] = target_h * 255.0
    hsv[:, :, 1] = np.clip(original_s * (target_s / ref_s), 0.0, 1.0) * 255.0
    value_scale = 1.0 + fade_weight * ((target_v / ref_v) - 1.0)
    hsv[:, :, 2] = np.clip(original_v * value_scale, 0.0, 1.0) * 255.0

    return Image.fromarray(np.rint(hsv).astype(np.uint8), "HSV").convert("RGB")


def make_contact_sheet(paths: list[Path]) -> Path:
    thumb_size = (216, 384)
    label_height = 38
    columns = 6
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_size[0], rows * (thumb_size[1] + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)

    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail(thumb_size, Image.Resampling.LANCZOS)
        x = (index % columns) * thumb_size[0]
        y = (index // columns) * (thumb_size[1] + label_height)
        sheet.paste(image, (x, y))
        draw.text((x + 8, y + thumb_size[1] + 8), path.stem.replace("_2160x3840", ""), fill="black", font=font)

    output = Path.home() / "AppData" / "Local" / "Temp" / "template-colors-31-60.jpg"
    sheet.save(output, quality=92, subsampling=0)
    return output


def main() -> None:
    if not REFERENCE_FILE.exists():
        raise FileNotFoundError(f"Reference template not found: {REFERENCE_FILE}")

    reference = Image.open(REFERENCE_FILE).convert("HSV")
    if reference.size != (2160, 3840):
        raise ValueError(f"Unexpected reference size: {reference.size}")

    reference_hsv = np.asarray(reference)
    generated: list[Path] = []
    for number, name, color in PALETTE:
        output = TEMPLATES_DIR / f"{number:02d}_{name}_2160x3840.png"
        recolor(reference_hsv, color).save(output, format="PNG", optimize=True)
        generated.append(output)
        print(output.name)

    print(f"Contact sheet: {make_contact_sheet(generated)}")


if __name__ == "__main__":
    main()
