from __future__ import annotations

import colorsys
import math
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


TEMPLATES_DIR = Path.home() / "Downloads" / "Templates"
CONTACT_SHEET = Path.home() / "AppData" / "Local" / "Temp" / "mystic-templates-96-145.jpg"

PALETTE = [
    (96, "Electric-Blue", "#0066FF"),
    (97, "Midnight-Blue", "#191970"),
    (98, "Sapphire", "#0F52BA"),
    (99, "Ultramarine", "#120A8F"),
    (100, "Arctic-Blue", "#A5F2F3"),
    (101, "Glacier", "#78CDE8"),
    (102, "Peacock", "#005F69"),
    (103, "Petrol", "#005F6B"),
    (104, "Lagoon", "#00A7A5"),
    (105, "Malachite", "#0BDA51"),
    (106, "Pine", "#01796F"),
    (107, "Clover", "#3EA055"),
    (108, "Fern", "#4F7942"),
    (109, "Bamboo", "#7BA05B"),
    (110, "Pistachio", "#93C572"),
    (111, "Neon-Lime", "#CCFF00"),
    (112, "Acid-Green", "#B0BF1A"),
    (113, "Apple", "#8DB600"),
    (114, "Avocado", "#568203"),
    (115, "Khaki", "#BDB76B"),
    (116, "Sunflower", "#FFDA03"),
    (117, "Saffron", "#F4C430"),
    (118, "Honey", "#EB9605"),
    (119, "Bronze", "#CD7F32"),
    (120, "Cinnamon", "#D2691E"),
    (121, "Mahogany", "#C04000"),
    (122, "Brick", "#B22222"),
    (123, "Garnet", "#733635"),
    (124, "Blood-Red", "#8A0303"),
    (125, "Fire", "#FF2D00"),
    (126, "Neon-Orange", "#FF5F1F"),
    (127, "Flamingo", "#FC8EAC"),
    (128, "Bubblegum", "#FFC1CC"),
    (129, "Hot-Pink", "#FF69B4"),
    (130, "Dusty-Rose", "#C9A9A6"),
    (131, "Blush", "#DE5D83"),
    (132, "Cranberry", "#9E003A"),
    (133, "Mulberry", "#770737"),
    (134, "Eggplant", "#614051"),
    (135, "Amethyst", "#9966CC"),
    (136, "Grape", "#6F2DA8"),
    (137, "Electric-Purple", "#BF00FF"),
    (138, "Neon-Violet", "#8F00FF"),
    (139, "Heliotrope", "#DF73FF"),
    (140, "Wisteria", "#C9A0DC"),
    (141, "Moonstone", "#3AA8C1"),
    (142, "Opal", "#A8C3BC"),
    (143, "Pearl", "#EAE0C8"),
    (144, "Smoke", "#738276"),
    (145, "Obsidian", "#1C1C1C"),
]


def hex_to_hsv(color: str) -> tuple[float, float, float]:
    color = color.lstrip("#")
    rgb = tuple(int(color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(*rgb)


def source_profile(path: Path) -> tuple[float, float]:
    with Image.open(path) as image:
        preview = image.convert("HSV")
        preview.thumbnail((270, 480), Image.Resampling.LANCZOS)
        hsv = np.asarray(preview, dtype=np.float32) / 255.0
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    mask = (saturation > 0.20) & (value < 0.92)
    if not np.any(mask):
        return 0.0, 0.0
    hues = hsv[:, :, 0][mask] * math.tau
    weights = saturation[mask] * (1.1 - value[mask])
    x = np.sum(np.cos(hues) * weights)
    y = np.sum(np.sin(hues) * weights)
    hue = (math.atan2(y, x) / math.tau) % 1.0
    strength = float(np.average(saturation[mask], weights=weights))
    return hue, strength


def hue_distance(first: float, second: float) -> float:
    delta = abs(first - second)
    return min(delta, 1.0 - delta)


def choose_source(
    target_h: float,
    target_s: float,
    target_v: float,
    sources: list[tuple[Path, float, float]],
    usage: Counter[Path],
) -> tuple[Path, float, float]:
    if target_s < 0.16:
        preferred_number = 63 if target_v < 0.45 else 64 if target_v < 0.82 else 95
        return next(item for item in sources if item[0].name.startswith(f"{preferred_number}_"))

    ranked = sorted(sources, key=lambda item: hue_distance(target_h, item[1]))[:7]
    return min(
        ranked,
        key=lambda item: hue_distance(target_h, item[1]) + usage[item[0]] * 0.035,
    )


def recolor(
    source: Image.Image,
    source_h: float,
    source_s: float,
    target_hex: str,
    mirror: bool,
) -> Image.Image:
    hsv = np.asarray(source.convert("HSV"), dtype=np.float32) / 255.0
    target_h, target_s, target_v = hex_to_hsv(target_hex)

    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    color_weight = np.clip(saturation / max(source_s, 0.18), 0.0, 1.0)
    shadow_weight = np.clip((0.94 - value) / 0.76, 0.0, 1.0)

    hsv[:, :, 0] = (hsv[:, :, 0] + (target_h - source_h)) % 1.0
    saturation_scale = np.clip(target_s / max(source_s, 0.18), 0.12, 1.75)
    hsv[:, :, 1] = np.clip(
        saturation * saturation_scale + shadow_weight * target_s * 0.08,
        0.0,
        1.0,
    )

    brightness_scale = np.clip(0.76 + target_v * 0.34, 0.78, 1.10)
    hsv[:, :, 2] = np.clip(
        value * (1.0 + color_weight * shadow_weight * (brightness_scale - 1.0)),
        0.0,
        1.0,
    )

    result = Image.fromarray(np.rint(hsv * 255.0).astype(np.uint8), "HSV").convert("RGB")
    if mirror:
        result = result.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return result


def make_contact_sheet(paths: list[Path]) -> None:
    tile = (216, 422)
    preview_size = (216, 384)
    columns = 5
    rows = math.ceil(len(paths) / columns)
    sheet = Image.new("RGB", (tile[0] * columns, tile[1] * rows), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 15)

    for index, path in enumerate(paths):
        with Image.open(path) as image:
            preview = image.convert("RGB")
            preview.thumbnail(preview_size, Image.Resampling.LANCZOS)
        x = index % columns * tile[0]
        y = index // columns * tile[1]
        sheet.paste(preview, (x, y))
        label = path.stem.replace("_2160x3840", "").replace("_Mystic-", " ")
        draw.text((x + 5, y + 389), label, fill="black", font=font)

    CONTACT_SHEET.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(CONTACT_SHEET, quality=93, subsampling=0)


def main() -> None:
    sources = []
    for path in sorted(TEMPLATES_DIR.glob("*_Mystic-*_2160x3840.png")):
        number = int(path.name.split("_", 1)[0])
        if 61 <= number <= 95:
            hue, saturation = source_profile(path)
            sources.append((path, hue, saturation))
    if len(sources) != 35:
        raise RuntimeError(f"Expected 35 mystical source templates, found {len(sources)}")

    outputs = [TEMPLATES_DIR / f"{number}_Mystic-{name}_2160x3840.png" for number, name, _ in PALETTE]
    collisions = [path for path in outputs if path.exists()]
    if collisions:
        raise FileExistsError(f"Refusing to overwrite existing templates: {collisions}")

    usage: Counter[Path] = Counter()
    generated: list[Path] = []
    for index, ((number, name, color), output) in enumerate(zip(PALETTE, outputs, strict=True)):
        target_h, target_s, target_v = hex_to_hsv(color)
        source_path, source_h, source_s = choose_source(target_h, target_s, target_v, sources, usage)
        usage[source_path] += 1
        with Image.open(source_path) as source:
            if source.size != (2160, 3840):
                raise ValueError(f"Unexpected source size: {source_path} -> {source.size}")
            result = recolor(source.convert("RGB"), source_h, source_s, color, mirror=index % 2 == 1)
        result.save(output, format="PNG", compress_level=6)
        generated.append(output)
        print(f"{output.name} <- {source_path.name}", flush=True)

    make_contact_sheet(generated)
    print(f"Contact sheet: {CONTACT_SHEET}")


if __name__ == "__main__":
    main()
