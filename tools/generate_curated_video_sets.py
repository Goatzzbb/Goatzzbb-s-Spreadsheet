from __future__ import annotations

import argparse
import itertools
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


CANVAS_SIZE = (2000, 3555)
PRODUCT_ZONE = (130, 220, 1870, 2280)
TEXT_ZONE = (150, 2440, 1850, 3260)
FONT_PATH = Path(r"C:\Windows\Fonts\times.ttf")
ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources"
NUMBER_NINE_ASSET_DIR = Path.home() / "AppData" / "Local" / "Temp" / "number_nine_internet"


NUMBER_NINE_DOWNLOADS = (
    (
        "01_faded_hanger.jpg",
        "https://media-assets.grailed.com/prd/listing/34051790/0c0fd6e6fa1f42409f3f2f06b9ab22b2?auto=format&fit=clip&w=1600",
    ),
    (
        "02_distressed_light.jpg",
        "https://media-assets.grailed.com/prd/listing/46548123/ad24869078dd40c4bc62cc25bd7058a2?auto=format&fit=clip&w=1600",
    ),
    (
        "03_damaged_indigo.jpg",
        "https://archive-factory.com/cdn/shop/files/3090053092128223_01_9029w.jpg?v=1758885230",
    ),
    (
        "04_black_slim.jpg",
        "https://media-assets.grailed.com/prd/listing/34062417/3a2d4ba2ae88457eb3c2a197027335cd?auto=format&fit=clip&w=1600",
    ),
    (
        "05_white_archive.jpg",
        "https://wastenot-official.com/cdn/shop/files/9026E090010-1.jpg?v=1779092637&width=2048",
    ),
    (
        "06_music_note.jpg",
        "https://media-assets.grailed.com/prd/listing/28901750/12f0c11dc1914d42ba5b393fe88aa2e2?auto=format&fit=clip&w=1600",
    ),
    (
        "10_zozo_slim.jpg",
        "https://c.imgz.jp/820/57326820/57326820b_34_d_500.jpg",
    ),
)


@dataclass(frozen=True)
class Item:
    name: str
    filename: str | Path
    crop: tuple[float, float, float, float] | None = None
    extraction: str = "auto"
    polygon: tuple[tuple[float, float], ...] | None = None


GREEN_ITEMS = (
    Item("Vetements Polizei Zip Hoodie", "cellImage_1421725185_1144.jpg"),
    Item("YVL / Carti Cap Camo", "newfinds_cellImage_295544988_1123.jpg"),
    Item("Corvidae Camo Puffer Jacket", "cellImage_1421725185_1908.jpg"),
    Item("Project GR Camo Shorts", "cellImage_1421725185_1553.jpg"),
    Item("ERD Camo Backpack", "legacy_external_68cf3d3a07c838c7.jpg"),
    Item("Chrome Hearts Caps", "cellImage_1421725185_3575.jpg"),
    Item("Number Nine x Supreme Varsity Jacket", "newfinds_cellImage_295544988_250.jpg"),
    Item("ERD Fox Fur Jacket", "cellImage_295544988_1040.jpg"),
    Item(
        "Supreme Heat Reactive Balaclava Mask",
        "cellImage_1421725185_3916.jpg",
        crop=(0.49, 0.0, 1.0, 1.0),
    ),
    Item(
        "Chrome Hearts Mesh Jersey",
        "cellImage_1421725185_1833.jpg",
        crop=(0.43, 0.01, 0.89, 0.55),
        extraction="green_strict",
    ),
    Item(
        "Bottega Veneta Orbit",
        "cellImage_1421725185_2929.jpg",
        crop=(0.50, 0.24, 1.0, 0.57),
    ),
    Item(
        "CDG PLAY Long Sleeve",
        "cellImage_1421725185_791.jpg",
        crop=(0.57, 0.0, 1.0, 1.0),
        extraction="green",
    ),
    Item("Adidas x Bape", "cellImage_295544988_744.jpg"),
    Item(
        "Unwanted Strawberry Mansion Hoodie",
        "cellImage_1421725185_1899.jpg",
        crop=(0.49, 0.0, 0.80, 1.0),
        extraction="green_strict",
    ),
    Item("Vlone Cap", "cellImage_1421725185_3982.jpg"),
    Item("Travis Scott Cactus Jack Backpack", "legacy_external_98afe1c280f7d95a.jpg"),
    Item("Number Nine x God Selection Shirt", "cellImage_1421725185_2590.jpg"),
    Item(
        "Nike Hot Step 2",
        "cellImage_1421725185_3106.jpg",
        crop=(0.0, 0.02, 0.50, 0.49),
        extraction="green",
        polygon=(
            (0.12, 0.16),
            (0.49, 0.08),
            (0.69, 0.17),
            (0.97, 0.44),
            (1.00, 0.64),
            (0.92, 0.80),
            (0.71, 0.91),
            (0.16, 0.86),
            (0.06, 0.66),
            (0.07, 0.38),
        ),
    ),
    Item(
        "Balenciaga Track 2 4.0",
        "cellImage_1421725185_2916.jpg",
        crop=(0.50, 0.01, 1.0, 0.52),
        extraction="green",
    ),
    Item("ERD Do What Thou Wilt Hoodie", "cellImage_1421725185_1842.jpg"),
)


BACKPACK_ITEMS = (
    Item("Christian Dior Backpack", "legacy_external_279540d18f7e9420.jpg"),
    Item("Louis Vuitton Backpack", "legacy_external_5c4c98a4b9b21ff2.jpg"),
    Item("ERD Camo Backpack", "legacy_external_68cf3d3a07c838c7.jpg"),
    Item("Alyx Backpack", "legacy_external_1d5e4c5b1403ca9b.jpg"),
    Item("Adidas Backpack", "legacy_external_6b8b9dfc7725a946.jpg"),
    Item("Bat Wings Backpack", "legacy_external_6c5a4f7ec1c2e1ba.jpg"),
    Item("Travis Scott Cactus Jack Backpack", "legacy_external_98afe1c280f7d95a.jpg"),
    Item("Chrome Hearts Leather Backpack", "legacy_external_b7c4d5a9b4a75183.jpg"),
    Item("Alyx 9SM Casual Backpack", "newfinds_cellImage_295544988_578.jpg"),
    Item(
        "Sprayground Backpack",
        "legacy_external_fa437bc4ed0f09d4.jpg",
        extraction="grabcut",
        polygon=(
            (0.44, 0.10),
            (0.60, 0.12),
            (0.69, 0.18),
            (0.73, 0.30),
            (0.74, 0.68),
            (0.70, 0.83),
            (0.61, 0.90),
            (0.48, 0.91),
            (0.39, 0.87),
            (0.31, 0.77),
            (0.26, 0.65),
            (0.27, 0.35),
            (0.28, 0.20),
            (0.35, 0.13),
        ),
    ),
    Item("Comme Des Garcons Backpack", "legacy_external_5e8bfdae62f631b2.jpg"),
    Item("Dior Backpack", "cellImage_1421725185_3654.jpg"),
    Item("Goyard Cisalpin Backpack", "cellImage_1421725185_3712.jpg"),
    Item("LV Monogram Paint Backpack", "cellImage_1421725185_3786.jpg"),
    Item("Baby Milo Backpack", "cellImage_1421725185_3496.jpg", crop=(0.0, 0.0, 0.52, 1.0)),
    Item("LV Christopher Backpack", "cellImage_1421725185_3783.jpg", crop=(0.51, 0.0, 1.0, 1.0)),
    Item("Maison Margiela Backpack", "cellImage_1421725185_3796.jpg", crop=(0.0, 0.0, 0.50, 1.0)),
    Item("Supreme FW17 Leopard Backpack", "cellImage_1421725185_3927.jpg", crop=(0.0, 0.0, 0.49, 1.0)),
    Item("Balenciaga x Adidas Backpack", "cellImage_1421725185_3516.jpg", crop=(0.0, 0.0, 0.515, 1.0)),
    Item("Bape Backpack", "cellImage_1421725185_3521.jpg"),
)


JEANS = {
    "Dior": (
        "newfinds_cellImage_295544988_477.jpg",
        "newfinds_cellImage_295544988_479.jpg",
        "newfinds_cellImage_295544988_476.jpg",
        "newfinds_cellImage_295544988_490.jpg",
        "newfinds_cellImage_295544988_486.jpg",
        Item(
            "",
            "newfinds_cellImage_295544988_481.jpg",
            crop=(0.12, 0.0, 0.84, 1.0),
            extraction="denim_floor",
        ),
    ),
    "Undercover": (
        "cellImage_295544988_504.jpg",
        "newfinds_cellImage_295544988_469.jpg",
        "cellImage_1421725185_1655.jpg",
        "cellImage_295544988_468.jpg",
        "cellImage_1421725185_1653.jpg",
        "cellImage_1421725185_1657.jpg",
    ),
    "Number Nine": (
        NUMBER_NINE_ASSET_DIR / "01_faded_hanger.jpg",
        NUMBER_NINE_ASSET_DIR / "07_studious_crushed.jpg",
        NUMBER_NINE_ASSET_DIR / "03_damaged_indigo.jpg",
        NUMBER_NINE_ASSET_DIR / "04_black_slim.jpg",
        Item(
            "",
            NUMBER_NINE_ASSET_DIR / "10_zozo_slim.jpg",
            polygon=(
                (0.29, 0.055),
                (0.70, 0.05),
                (0.73, 0.10),
                (0.70, 0.95),
                (0.52, 0.95),
                (0.53, 0.82),
                (0.53, 0.67),
                (0.55, 0.58),
                (0.54, 0.50),
                (0.525, 0.44),
                (0.50, 0.40),
                (0.455, 0.44),
                (0.43, 0.50),
                (0.42, 0.58),
                (0.45, 0.67),
                (0.46, 0.82),
                (0.48, 0.95),
                (0.31, 0.95),
                (0.28, 0.70),
                (0.27, 0.45),
                (0.26, 0.20),
                (0.27, 0.10),
            ),
        ),
        NUMBER_NINE_ASSET_DIR / "06_music_note.jpg",
    ),
}


LOGOS = {
    "Dior": (
        "dior.png",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Dior%20Logo%202022.svg?width=1800",
    ),
    "Undercover": (
        "undercover.jpg",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Undercover-logo.jpg?width=1800",
    ),
    "Number Nine": (
        "number-nine.png",
        "https://commons.wikimedia.org/wiki/Special:Redirect/file/Number%20%28N%29ine%20Logo.png?width=1800",
    ),
}


def normalized_crop(image: Image.Image, crop: tuple[float, float, float, float] | None) -> Image.Image:
    if crop is None:
        return image
    left, top, right, bottom = crop
    return image.crop(
        (
            round(left * image.width),
            round(top * image.height),
            round(right * image.width),
            round(bottom * image.height),
        )
    )


def connected_border_mask(candidate: np.ndarray) -> np.ndarray:
    count, labels = cv2.connectedComponents(candidate.astype(np.uint8), connectivity=8)
    if count <= 1:
        return candidate
    border_labels = np.unique(
        np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1]))
    )
    border_labels = border_labels[border_labels != 0]
    return np.isin(labels, border_labels)


def edge_background_alpha(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    height, width = rgb.shape[:2]
    strip = max(2, round(min(width, height) * 0.012))
    border = np.concatenate(
        (
            rgb[:strip].reshape(-1, 3),
            rgb[-strip:].reshape(-1, 3),
            rgb[:, :strip].reshape(-1, 3),
            rgb[:, -strip:].reshape(-1, 3),
        )
    )
    background = np.median(border, axis=0)
    spread = float(np.median(np.linalg.norm(border.astype(np.float32) - background, axis=1)))

    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    background_lab = cv2.cvtColor(
        np.uint8([[background.round().astype(np.uint8)]]), cv2.COLOR_RGB2LAB
    )[0, 0].astype(np.float32)
    distance = np.linalg.norm(lab - background_lab, axis=2)
    luminance = float(background.mean())
    if luminance >= 185:
        threshold = 57.0
    elif luminance >= 80:
        threshold = 41.0
    else:
        threshold = 27.0
    threshold += min(6.0, spread * 0.20)
    connected_background = connected_border_mask(distance <= threshold)

    alpha = np.where(connected_background, 0, 255).astype(np.uint8)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.75)

    alpha_float = alpha.astype(np.float32) / 255.0
    observed = rgb.astype(np.float32)
    safe_alpha = np.maximum(alpha_float[..., None], 0.09)
    clean = (observed - background[None, None, :] * (1.0 - alpha_float[..., None])) / safe_alpha
    clean = np.where(alpha_float[..., None] >= 0.995, observed, clean)

    rgba = np.dstack((np.clip(clean, 0, 255).astype(np.uint8), alpha))
    return Image.fromarray(rgba, mode="RGBA")


def grabcut_alpha(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    height, width = rgb.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    rect = (
        max(1, round(width * 0.035)),
        max(1, round(height * 0.025)),
        max(2, round(width * 0.93)),
        max(2, round(height * 0.95)),
    )
    background_model = np.zeros((1, 65), np.float64)
    foreground_model = np.zeros((1, 65), np.float64)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    cv2.grabCut(
        bgr,
        mask,
        rect,
        background_model,
        foreground_model,
        7,
        cv2.GC_INIT_WITH_RECT,
    )
    foreground = np.isin(mask, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8) * 255
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    foreground = cv2.GaussianBlur(foreground, (0, 0), 0.8)
    rgba = np.dstack((rgb, foreground))
    return Image.fromarray(rgba, mode="RGBA")


def denim_floor_alpha(image: Image.Image) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    height, width = rgb.shape[:2]
    outline = (
        (0.10, 0.02),
        (0.87, 0.02),
        (0.84, 0.98),
        (0.59, 0.98),
        (0.62, 0.82),
        (0.60, 0.66),
        (0.56, 0.52),
        (0.51, 0.38),
        (0.47, 0.38),
        (0.42, 0.52),
        (0.39, 0.66),
        (0.38, 0.82),
        (0.40, 0.98),
        (0.09, 0.98),
        (0.13, 0.33),
    )
    silhouette = np.zeros((height, width), dtype=np.uint8)
    points = np.asarray(
        [(round(x * width), round(y * height)) for x, y in outline], dtype=np.int32
    )
    cv2.fillPoly(silhouette, [points], 255)

    hue, saturation, value = cv2.split(cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV))
    mask = np.full((height, width), cv2.GC_BGD, dtype=np.uint8)
    mask[silhouette > 0] = cv2.GC_PR_FGD
    pale_floor = (saturation < 30) & (value > 150) & (silhouette > 0)
    mask[pale_floor] = cv2.GC_PR_BGD
    blue_or_dark = (
        (((hue >= 85) & (hue <= 125) & (saturation >= 28)) | (value < 82))
        & (silhouette > 0)
    )
    mask[blue_or_dark] = cv2.GC_FGD
    mask[(saturation < 28) & (value > 185) & (silhouette > 0)] = cv2.GC_BGD

    background_model = np.zeros((1, 65), np.float64)
    foreground_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(
        cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
        mask,
        None,
        background_model,
        foreground_model,
        8,
        cv2.GC_INIT_WITH_MASK,
    )
    alpha = np.isin(mask, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8) * 255
    count, labels, stats, _ = cv2.connectedComponentsWithStats(alpha, connectivity=8)
    if count > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        alpha = np.where(labels == largest, 255, 0).astype(np.uint8)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.65)
    return Image.fromarray(np.dstack((rgb, alpha)), mode="RGBA")


def green_guided_alpha(image: Image.Image, strict: bool = False) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    base = np.asarray(edge_background_alpha(image).getchannel("A"), dtype=np.uint8)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hue, saturation, value = cv2.split(hsv)
    green = (
        (hue >= 28)
        & (hue <= 105)
        & (saturation >= 45)
        & (value >= 24)
        & (base >= 80)
    ).astype(np.uint8)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(green, connectivity=8)
    if count <= 1:
        return Image.fromarray(np.dstack((rgb, base)), mode="RGBA")
    useful = [index for index in range(1, count) if stats[index, cv2.CC_STAT_AREA] >= 8]
    if not useful:
        return Image.fromarray(np.dstack((rgb, base)), mode="RGBA")
    seed = np.isin(labels, useful).astype(np.uint8)

    points = np.column_stack(np.where(seed > 0))[:, ::-1].astype(np.int32)
    hull = cv2.convexHull(points)
    region = np.zeros_like(seed)
    cv2.fillConvexPoly(region, hull, 255)
    radius = max(7, round(min(image.size) * 0.025))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
    region = cv2.dilate(region, kernel, iterations=1)

    mask = np.full(seed.shape, cv2.GC_BGD, dtype=np.uint8)
    probable = (base >= 55) & (region > 0)
    mask[probable] = cv2.GC_PR_FGD
    mask[seed > 0] = cv2.GC_FGD
    colorful_other = (saturation > 75) & ((hue < 20) | (hue > 112)) & (region > 0)
    protected = cv2.dilate(seed, np.ones((11, 11), np.uint8), iterations=1) > 0
    mask[colorful_other & ~protected] = cv2.GC_PR_BGD

    background_model = np.zeros((1, 65), np.float64)
    foreground_model = np.zeros((1, 65), np.float64)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    cv2.grabCut(
        bgr,
        mask,
        None,
        background_model,
        foreground_model,
        6,
        cv2.GC_INIT_WITH_MASK,
    )
    foreground = np.isin(mask, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8) * 255
    foreground = np.minimum(foreground, base)
    if strict:
        protected = cv2.dilate(seed, np.ones((9, 9), np.uint8), iterations=1) > 0
        wrong_color = (saturation > 70) & ((hue < 18) | (hue > 94)) & ~protected
        foreground[wrong_color] = 0
        component_count, components = cv2.connectedComponents((foreground > 40).astype(np.uint8), connectivity=8)
        if component_count > 1:
            touching_seed = np.unique(components[seed > 0])
            touching_seed = touching_seed[touching_seed != 0]
            foreground[~np.isin(components, touching_seed)] = 0
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    foreground = cv2.GaussianBlur(foreground, (0, 0), 0.75)
    return Image.fromarray(np.dstack((rgb, foreground)), mode="RGBA")


def apply_polygon(image: Image.Image, polygon: tuple[tuple[float, float], ...]) -> Image.Image:
    scale = 4
    mask = Image.new("L", (image.width * scale, image.height * scale), 0)
    points = [(round(x * mask.width), round(y * mask.height)) for x, y in polygon]
    ImageDraw.Draw(mask).polygon(points, fill=255)
    mask = mask.resize(image.size, Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(0.35))
    alpha = Image.fromarray(
        np.minimum(np.asarray(image.getchannel("A")), np.asarray(mask)).astype(np.uint8),
        mode="L",
    )
    result = image.copy()
    result.putalpha(alpha)
    return result


def trim_transparency(image: Image.Image) -> Image.Image:
    alpha = np.asarray(image.getchannel("A"))
    ys, xs = np.where(alpha > 18)
    if not len(xs):
        return image
    padding = max(4, round(max(image.size) * 0.012))
    box = (
        max(0, int(xs.min()) - padding),
        max(0, int(ys.min()) - padding),
        min(image.width, int(xs.max()) + padding + 1),
        min(image.height, int(ys.max()) + padding + 1),
    )
    return image.crop(box)


def extract_item(item: Item | Path) -> Image.Image:
    if isinstance(item, Item):
        candidate = Path(item.filename)
        source_path = candidate if candidate.is_absolute() else RESOURCES / candidate
        crop = item.crop
        extraction = item.extraction
    else:
        source_path = item
        crop = None
        extraction = "auto"

    with Image.open(source_path) as opened:
        source = normalized_crop(ImageOps.exif_transpose(opened).convert("RGBA"), crop)
    if source.getchannel("A").getextrema()[0] < 250:
        cutout = source
    elif extraction == "grabcut":
        cutout = grabcut_alpha(source)
    elif extraction == "denim_floor":
        cutout = denim_floor_alpha(source)
    elif extraction in ("green", "green_strict"):
        cutout = green_guided_alpha(source, strict=extraction == "green_strict")
    else:
        cutout = edge_background_alpha(source)
    if isinstance(item, Item) and item.polygon is not None:
        cutout = apply_polygon(cutout, item.polygon)
    return trim_transparency(cutout)


def fit_image(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    scale = min(max_width / image.width, max_height / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def shadow_layer(
    canvas_size: tuple[int, int],
    alpha: Image.Image,
    position: tuple[int, int],
    offset: tuple[int, int],
    blur: float,
    opacity: float,
    shrink: int = 3,
) -> Image.Image:
    mask = alpha
    if shrink >= 3:
        mask = mask.filter(ImageFilter.MinFilter(shrink if shrink % 2 else shrink + 1))
    placed = Image.new("L", canvas_size, 0)
    placed.paste(mask, (position[0] + offset[0], position[1] + offset[1]))
    placed = placed.filter(ImageFilter.GaussianBlur(blur))
    placed = placed.point(lambda value: round(value * opacity))
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    layer.putalpha(placed)
    return layer


def place_with_shadow(
    canvas: Image.Image,
    cutout: Image.Image,
    position: tuple[int, int],
    subtle: bool = False,
) -> None:
    alpha = cutout.getchannel("A")
    if subtle:
        canvas.alpha_composite(shadow_layer(canvas.size, alpha, position, (22, 30), 15, 0.21, 3))
        canvas.alpha_composite(shadow_layer(canvas.size, alpha, position, (8, 11), 5, 0.10, 3))
    else:
        canvas.alpha_composite(shadow_layer(canvas.size, alpha, position, (58, 72), 31, 0.24, 5))
        canvas.alpha_composite(shadow_layer(canvas.size, alpha, position, (24, 32), 11, 0.16, 3))
    canvas.alpha_composite(cutout, position)


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def balanced_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    counts: tuple[int, ...],
) -> list[str] | None:
    words = text.split()
    best: tuple[float, list[str]] | None = None
    for count in counts:
        if count < 1 or count > len(words):
            continue
        for breaks in itertools.combinations(range(1, len(words)), count - 1):
            points = (0, *breaks, len(words))
            lines = [" ".join(words[points[i] : points[i + 1]]) for i in range(count)]
            widths = [text_width(draw, line, font) for line in lines]
            if max(widths) > max_width:
                continue
            raggedness = (max(widths) - min(widths)) ** 2 if len(widths) > 1 else 0
            score = max(widths) + raggedness / max_width
            if best is None or score < best[0]:
                best = (score, lines)
    return best[1] if best else None


def draw_product_name(canvas: Image.Image, name: str) -> None:
    draw = ImageDraw.Draw(canvas)
    left, top, right, bottom = TEXT_ZONE
    max_width = right - left
    selected_font: ImageFont.FreeTypeFont | None = None
    selected_lines: list[str] | None = None

    preferred = (1,) if len(name.split()) == 1 else (2,)
    for size in range(205, 144, -5):
        font = ImageFont.truetype(str(FONT_PATH), size)
        lines = balanced_lines(draw, name, font, max_width, preferred)
        if lines:
            selected_font, selected_lines = font, lines
            break
    if selected_lines is None:
        for size in range(200, 119, -5):
            font = ImageFont.truetype(str(FONT_PATH), size)
            lines = balanced_lines(draw, name, font, max_width, (3,))
            if lines:
                selected_font, selected_lines = font, lines
                break
    if selected_font is None or selected_lines is None:
        selected_font = ImageFont.truetype(str(FONT_PATH), 120)
        selected_lines = [name]

    spacing = max(22, round(selected_font.size * 0.20))
    boxes = [draw.textbbox((0, 0), line, font=selected_font) for line in selected_lines]
    heights = [box[3] - box[1] for box in boxes]
    y = top + (bottom - top - sum(heights) - spacing * (len(heights) - 1)) // 2

    shadow = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    placements: list[tuple[int, int, str]] = []
    for line, box, height in zip(selected_lines, boxes, heights):
        width = box[2] - box[0]
        x = (canvas.width - width) // 2
        baseline_y = y - box[1]
        placements.append((x, baseline_y, line))
        shadow_draw.text((x + 13, baseline_y + 16), line, font=selected_font, fill=(0, 0, 0, 115))
        y += height + spacing
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(11)))
    draw = ImageDraw.Draw(canvas)
    for x, y, line in placements:
        draw.text((x, y), line, font=selected_font, fill="black")


def safe_name(index: int, name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-")
    return f"{index:02d}_{slug}.png"


def make_find_slide(item: Item, output_path: Path) -> None:
    canvas = Image.new("RGBA", CANVAS_SIZE, "white")
    cutout = extract_item(item)
    left, top, right, bottom = PRODUCT_ZONE
    cutout = fit_image(cutout, right - left, bottom - top)
    position = ((canvas.width - cutout.width) // 2, top + (bottom - top - cutout.height) // 2)
    place_with_shadow(canvas, cutout, position)
    draw_product_name(canvas, item.name)
    save_png(canvas, output_path)


def save_png(image: Image.Image, output_path: Path) -> None:
    temporary = output_path.with_name(f".{output_path.stem}.rendering.png")
    image.convert("RGB").save(temporary, format="PNG", optimize=True)
    temporary.replace(output_path)


def download_logos(directory: Path) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}
    for brand, (filename, url) in LOGOS.items():
        destination = directory / filename
        if not destination.exists():
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=45) as response:
                destination.write_bytes(response.read())
        result[brand] = destination
    return result


def download_number_nine_images() -> None:
    NUMBER_NINE_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in NUMBER_NINE_DOWNLOADS:
        destination = NUMBER_NINE_ASSET_DIR / filename
        if destination.exists():
            continue
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=45) as response:
            destination.write_bytes(response.read())


def logo_cutout(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        image = opened.convert("RGBA")
    if image.getchannel("A").getextrema()[0] < 250:
        return trim_transparency(image)
    return trim_transparency(edge_background_alpha(image))


def make_brand_slide(
    brand: str,
    files: tuple[str | Path | Item, ...],
    logo_path: Path,
    output_path: Path,
) -> None:
    canvas = Image.new("RGBA", CANVAS_SIZE, "white")
    logo = fit_image(logo_cutout(logo_path), 1450, 360)
    logo_position = ((canvas.width - logo.width) // 2, 125 + (360 - logo.height) // 2)
    canvas.alpha_composite(logo, logo_position)

    columns = (90, 705, 1320)
    rows = (575, 1940)
    cell_width, cell_height = 590, 1250
    for index, entry in enumerate(files):
        row, column = divmod(index, 3)
        if isinstance(entry, Item):
            source: Item | Path = entry
        elif isinstance(entry, Path):
            source = entry
        else:
            source = RESOURCES / entry
        cutout = extract_item(source)

        max_width, max_height = 540, 1170
        if brand == "Dior" and index == 5:
            max_width, max_height = 650, 1230
        elif brand == "Undercover" and index == 0:
            max_width, max_height = 720, 1220
        elif brand == "Undercover" and index == 5:
            max_width, max_height = 730, 1220
        elif brand == "Number Nine":
            max_width, max_height = 620, 1180
        cutout = fit_image(cutout, max_width, max_height)
        x = columns[column] + (cell_width - cutout.width) // 2
        y = rows[row] + (cell_height - cutout.height) // 2
        place_with_shadow(canvas, cutout, (x, y), subtle=True)

    save_png(canvas, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the three curated video image sets")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(r"C:\Users\micha\Downloads\Finds"),
    )
    parser.add_argument(
        "--only",
        choices=("vid1", "vid2", "vid3"),
        action="append",
        help="Render only the selected video set; may be repeated.",
    )
    args = parser.parse_args()
    selected = set(args.only or ("vid1", "vid2", "vid3"))
    output_root = args.output.resolve()
    green_output = output_root / "Vid1_Gruene_Finds"
    backpack_output = output_root / "Vid2_Rucksaecke"
    jeans_output = output_root / "Vid3_Jeans_Brands"
    for directory in (green_output, backpack_output, jeans_output):
        directory.mkdir(parents=True, exist_ok=True)

    if "vid1" in selected:
        for index, item in enumerate(GREEN_ITEMS, start=1):
            path = green_output / safe_name(index, item.name)
            make_find_slide(item, path)
            print(f"Vid1 {index:02d}/20: {item.name}")

    if "vid2" in selected:
        for index, item in enumerate(BACKPACK_ITEMS, start=1):
            path = backpack_output / safe_name(index, item.name)
            make_find_slide(item, path)
            print(f"Vid2 {index:02d}/20: {item.name}")

    if "vid3" in selected:
        download_number_nine_images()
        logo_paths = download_logos(Path.home() / "AppData" / "Local" / "Temp" / "codex_brand_logos")
        for index, (brand, files) in enumerate(JEANS.items(), start=1):
            path = jeans_output / f"{index:02d}_{brand.replace(' ', '_')}_Jeans.png"
            make_brand_slide(brand, files, logo_paths[brand], path)
            print(f"Vid3 {index:02d}/03: {brand}")


if __name__ == "__main__":
    main()
