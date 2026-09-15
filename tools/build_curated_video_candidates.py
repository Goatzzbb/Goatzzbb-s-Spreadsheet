from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from lxml import html
from PIL import Image, ImageDraw, ImageFont, ImageOps


@dataclass(frozen=True)
class Candidate:
    name: str
    image_path: Path
    link: str
    width: int
    height: int
    white_ratio: float
    occupied_ratio: float
    green_ratio: float
    score: float


def load_generator(path: Path):
    spec = importlib.util.spec_from_file_location("find_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_rows(index_path: Path, clean_name) -> list[tuple[str, Path, str]]:
    document = html.parse(str(index_path))
    rows: list[tuple[str, Path, str]] = []
    for row in document.xpath("//tbody/tr"):
        cells = row.xpath("./td")
        sources = row.xpath(".//img/@src")
        if len(cells) < 5 or not sources:
            continue
        raw_name = " ".join(" ".join(cells[2].itertext()).split())
        image_path = index_path.parent / sources[0]
        links = cells[4].xpath(".//a/@href")
        if raw_name and image_path.exists():
            rows.append((clean_name(raw_name), image_path, links[0] if links else ""))
    return rows


def image_metrics(name: str, image_path: Path, link: str) -> Candidate | None:
    try:
        with Image.open(image_path) as source:
            width, height = source.size
            if min(width, height) < 250 or max(width, height) < 400:
                return None
            preview = ImageOps.contain(source.convert("RGB"), (260, 260), Image.Resampling.LANCZOS)
    except (OSError, ValueError):
        return None

    pixels = np.asarray(preview, dtype=np.float32) / 255.0
    maximum = pixels.max(axis=2)
    minimum = pixels.min(axis=2)
    saturation = np.divide(
        maximum - minimum,
        maximum,
        out=np.zeros_like(maximum),
        where=maximum > 0.001,
    )
    white = np.all(pixels > 0.93, axis=2)
    foreground = ~np.all(pixels > 0.965, axis=2)
    occupied = float(foreground.mean())
    if occupied < 0.06:
        return None

    red, green, blue = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
    green_pixels = (
        foreground
        & (saturation > 0.16)
        & (green > red * 1.08)
        & (green > blue * 1.03)
        & (green > 0.16)
    )
    green_ratio = float(green_pixels.sum() / max(1, foreground.sum()))
    white_ratio = float(white.mean())
    resolution_score = min(1.0, math.sqrt(width * height) / 1800.0)
    background_score = min(1.0, white_ratio / 0.55)
    occupancy_score = 1.0 - min(1.0, abs(occupied - 0.48) / 0.48)
    score = resolution_score * 0.45 + background_score * 0.35 + occupancy_score * 0.20
    return Candidate(
        name=name,
        image_path=image_path,
        link=link,
        width=width,
        height=height,
        white_ratio=white_ratio,
        occupied_ratio=occupied,
        green_ratio=green_ratio,
        score=score,
    )


def unique_by_name(candidates: list[Candidate]) -> list[Candidate]:
    selected: dict[str, Candidate] = {}
    for candidate in candidates:
        key = candidate.name.casefold()
        if key not in selected or candidate.score > selected[key].score:
            selected[key] = candidate
    return list(selected.values())


def wrap_label(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> str:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if not current or draw.textlength(candidate, font=font) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return "\n".join(lines[:3])


def write_sheet(candidates: list[Candidate], output_path: Path, title: str) -> None:
    columns = 4
    cell_width, cell_height = 460, 520
    header_height = 80
    rows = math.ceil(len(candidates) / columns)
    sheet = Image.new("RGB", (columns * cell_width, header_height + rows * cell_height), "#eeeeee")
    draw = ImageDraw.Draw(sheet)
    title_font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 34)
    label_font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 22)
    draw.text((24, 20), title, font=title_font, fill="black")

    for index, candidate in enumerate(candidates, start=1):
        row, column = divmod(index - 1, columns)
        x0 = column * cell_width
        y0 = header_height + row * cell_height
        draw.rectangle((x0 + 5, y0 + 5, x0 + cell_width - 5, y0 + cell_height - 5), fill="white")
        with Image.open(candidate.image_path) as source:
            preview = ImageOps.contain(source.convert("RGB"), (420, 385), Image.Resampling.LANCZOS)
        x = x0 + (cell_width - preview.width) // 2
        y = y0 + 12 + (385 - preview.height) // 2
        sheet.paste(preview, (x, y))
        label = wrap_label(draw, f"{index:02d}  {candidate.name}", label_font, 420)
        draw.multiline_text((x0 + 20, y0 + 405), label, font=label_font, fill="black", spacing=2)
        metrics = f"{candidate.width}x{candidate.height}  W:{candidate.white_ratio:.2f}  G:{candidate.green_ratio:.2f}"
        draw.text((x0 + 20, y0 + 486), metrics, font=label_font, fill="#555555")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def write_manifest(candidates: list[Candidate], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["position", "name", "image_path", "link", "width", "height", "white_ratio", "occupied_ratio", "green_ratio", "score"]
        )
        for index, candidate in enumerate(candidates, start=1):
            writer.writerow(
                [
                    index,
                    candidate.name,
                    candidate.image_path,
                    candidate.link,
                    candidate.width,
                    candidate.height,
                    f"{candidate.white_ratio:.4f}",
                    f"{candidate.occupied_ratio:.4f}",
                    f"{candidate.green_ratio:.4f}",
                    f"{candidate.score:.4f}",
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=Path("index.html"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    index_path = args.index.resolve()
    generator = load_generator(Path("tools/generate_find_slides.py").resolve())
    rows = parse_rows(index_path, generator.clean_name)
    measured: list[Candidate] = []
    for position, (name, image_path, link) in enumerate(rows, start=1):
        candidate = image_metrics(name, image_path, link)
        if candidate:
            measured.append(candidate)
        if position % 500 == 0:
            print(f"Measured {position}/{len(rows)}")

    green_terms = ("green", "olive", "khaki", "lime", "moss", "jade", "emerald", "army", "camo")
    green = unique_by_name(
        [
            item
            for item in measured
            if min(item.width, item.height) >= 420
            and max(item.width, item.height) >= 650
            and item.white_ratio >= 0.10
            and (item.green_ratio >= 0.012 or any(term in item.name.casefold() for term in green_terms))
        ]
    )
    green.sort(
        key=lambda item: (
            item.green_ratio * 0.62
            + item.score * 0.23
            + (0.15 if any(term in item.name.casefold() for term in green_terms) else 0.0)
        ),
        reverse=True,
    )
    green = green[:100]

    backpacks = [
        item
        for item in measured
        if min(item.width, item.height) >= 250
        and max(item.width, item.height) >= 400
        and any(term in item.name.casefold() for term in ("backpack", "back pack", "daypack"))
        and "doesn't look" not in item.name.casefold()
    ]
    backpacks.sort(key=lambda item: (item.white_ratio * 0.40 + item.score * 0.60), reverse=True)
    backpacks = backpacks[:80]

    def jeans_for(brand_terms: tuple[str, ...]) -> list[Candidate]:
        result = [
            item
            for item in measured
            if any(term in item.name.casefold() for term in brand_terms)
            and any(term in item.name.casefold() for term in ("jeans", "denim"))
            and "jacket" not in item.name.casefold()
        ]
        result.sort(key=lambda item: item.score, reverse=True)
        return result[:48]

    groups = {
        "green": green,
        "backpacks": backpacks,
        "dior_jeans": jeans_for(("dior",)),
        "undercover_jeans": jeans_for(("undercover",)),
        "number_nine_jeans": jeans_for(("number nine", "number (n)ine", "numbernine")),
    }
    for key, candidates in groups.items():
        write_sheet(candidates, args.output / f"{key}_candidates.jpg", key.replace("_", " ").title())
        write_manifest(candidates, args.output / f"{key}_candidates.csv")
        print(f"{key}: {len(candidates)}")


if __name__ == "__main__":
    main()
