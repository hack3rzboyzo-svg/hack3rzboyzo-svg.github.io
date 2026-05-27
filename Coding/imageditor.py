"""
Dataset Image Augmentor
========================
Generates hundreds of augmented images from a single source image.
Augmentations: blur, brightness, contrast, saturation, rotation,
flip, crop, noise, hue shift, sharpness, perspective, and more.

Requirements:
    pip install Pillow numpy

Usage:
    python augment_dataset.py --input your_image.jpg --output ./dataset --count 500
"""

import argparse
import os
import random
import sys
from pathlib import Path

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    import numpy as np
except ImportError:
    print("Missing dependencies. Run: pip install Pillow numpy")
    sys.exit(1)


# ─────────────────────────────────────────────
#  Individual augmentation functions
# ─────────────────────────────────────────────

def aug_blur(img):
    """Gaussian blur with random radius."""
    radius = random.uniform(0.5, 4.0)
    return img.filter(ImageFilter.GaussianBlur(radius=radius))


def aug_sharpen(img):
    """Unsharp mask sharpening."""
    factor = random.uniform(1.5, 4.0)
    enhancer = ImageEnhance.Sharpness(img)
    return enhancer.enhance(factor)


def aug_brightness(img):
    """Random brightness shift."""
    factor = random.uniform(0.4, 1.8)
    return ImageEnhance.Brightness(img).enhance(factor)


def aug_contrast(img):
    """Random contrast adjustment."""
    factor = random.uniform(0.4, 2.0)
    return ImageEnhance.Contrast(img).enhance(factor)


def aug_saturation(img):
    """Random saturation — from desaturated to highly vivid."""
    factor = random.uniform(0.0, 3.5)
    return ImageEnhance.Color(img).enhance(factor)


def aug_rotate(img):
    """Rotation with optional transparent fill for out-of-frame areas."""
    angle = random.uniform(-30, 30)
    fill_color = (
        (random.randint(0, 255),) * 3
        if img.mode == "RGB"
        else (random.randint(0, 255),) * 4
    )
    return img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=fill_color)


def aug_flip_h(img):
    """Horizontal flip."""
    return ImageOps.mirror(img)


def aug_flip_v(img):
    """Vertical flip."""
    return ImageOps.flip(img)


def aug_crop_zoom(img):
    """Random crop then resize back to original — simulates zoom."""
    w, h = img.size
    crop_pct = random.uniform(0.65, 0.95)
    new_w, new_h = int(w * crop_pct), int(h * crop_pct)
    left = random.randint(0, w - new_w)
    top  = random.randint(0, h - new_h)
    cropped = img.crop((left, top, left + new_w, top + new_h))
    return cropped.resize((w, h), Image.LANCZOS)


def aug_noise(img):
    """Add random Gaussian noise to pixel values."""
    arr = np.array(img).astype(np.int16)
    sigma = random.uniform(5, 40)
    noise = np.random.normal(0, sigma, arr.shape).astype(np.int16)
    noisy = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy)


def aug_hue_shift(img):
    """Shift hue by converting through HSV space using numpy."""
    arr = np.array(img.convert("RGB")).astype(np.uint8)
    # Simple hue shift via channel roll
    shift = random.randint(10, 80)
    arr = np.roll(arr, shift, axis=2)
    return Image.fromarray(arr).convert(img.mode)


def aug_pixelate(img):
    """Low-res pixelation effect."""
    w, h = img.size
    scale = random.uniform(0.05, 0.25)
    small = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.NEAREST)
    return small.resize((w, h), Image.NEAREST)


def aug_grayscale(img):
    """Convert to grayscale (kept as RGB tensor)."""
    gray = ImageOps.grayscale(img)
    return gray.convert(img.mode)


def aug_sepia(img):
    """Apply a warm sepia tone."""
    arr = np.array(img.convert("RGB")).astype(np.float32)
    r = arr[:,:,0] * 0.393 + arr[:,:,1] * 0.769 + arr[:,:,2] * 0.189
    g = arr[:,:,0] * 0.349 + arr[:,:,1] * 0.686 + arr[:,:,2] * 0.168
    b = arr[:,:,0] * 0.272 + arr[:,:,1] * 0.534 + arr[:,:,2] * 0.131
    sepia = np.stack([r, g, b], axis=2)
    sepia = np.clip(sepia, 0, 255).astype(np.uint8)
    return Image.fromarray(sepia).convert(img.mode)


def aug_perspective(img):
    """Slight random perspective warp."""
    w, h = img.size
    d = random.uniform(0.03, 0.12)
    dx1 = random.uniform(0, d * w)
    dy1 = random.uniform(0, d * h)
    dx2 = random.uniform(0, d * w)
    dy2 = random.uniform(0, d * h)
    coeffs = (
        dx1, dy1,
        w - dx2, dy2,
        dx2, h - dy2,
        w - dx1, h - dy1,
    )
    return img.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC)


def aug_posterize(img):
    """Reduce color depth."""
    bits = random.randint(2, 5)
    return ImageOps.posterize(img.convert("RGB"), bits).convert(img.mode)


def aug_equalize(img):
    """Histogram equalization for contrast normalisation."""
    return ImageOps.equalize(img.convert("RGB")).convert(img.mode)


# Registry of all augmentations
ALL_AUGMENTATIONS = [
    ("blur",        aug_blur),
    ("sharpen",     aug_sharpen),
    ("brightness",  aug_brightness),
    ("contrast",    aug_contrast),
    ("saturation",  aug_saturation),
    ("rotate",      aug_rotate),
    ("flip_h",      aug_flip_h),
    ("flip_v",      aug_flip_v),
    ("crop_zoom",   aug_crop_zoom),
    ("noise",       aug_noise),
    ("hue_shift",   aug_hue_shift),
    ("pixelate",    aug_pixelate),
    ("grayscale",   aug_grayscale),
    ("sepia",       aug_sepia),
    ("perspective", aug_perspective),
    ("posterize",   aug_posterize),
    ("equalize",    aug_equalize),
]


# ─────────────────────────────────────────────
#  Core generation logic
# ─────────────────────────────────────────────

def apply_random_augmentations(img, min_augs=1, max_augs=4):
    """Apply a random subset of augmentations to an image."""
    augs = random.sample(ALL_AUGMENTATIONS, k=random.randint(min_augs, max_augs))
    applied_names = []
    for name, fn in augs:
        try:
            img = fn(img)
            applied_names.append(name)
        except Exception as e:
            # Skip a failing augmentation silently
            pass
    return img, applied_names


def generate_dataset(
    source_path: str,
    output_dir: str,
    count: int = 300,
    min_augs: int = 1,
    max_augs: int = 4,
    output_format: str = "JPEG",
    quality: int = 90,
    verbose: bool = True,
):
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source image not found: {source_path}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base_img = Image.open(source)
    # Ensure RGB so all augmentations work cleanly
    if base_img.mode not in ("RGB", "RGBA"):
        base_img = base_img.convert("RGB")

    ext = "jpg" if output_format.upper() == "JPEG" else output_format.lower()
    stem = source.stem

    aug_counter = {}
    print(f"\n🖼  Source : {source}")
    print(f"📁  Output : {out_dir.resolve()}")
    print(f"🔢  Count  : {count} images\n")

    for i in range(1, count + 1):
        img_copy = base_img.copy()
        augmented, applied = apply_random_augmentations(img_copy, min_augs, max_augs)

        for a in applied:
            aug_counter[a] = aug_counter.get(a, 0) + 1

        tag = "_".join(applied)
        filename = out_dir / f"{stem}_{i:04d}_{tag}.{ext}"

        save_kwargs = {"format": output_format}
        if output_format.upper() == "JPEG":
            save_kwargs["quality"] = quality
            augmented = augmented.convert("RGB")

        augmented.save(str(filename), **save_kwargs)

        if verbose and (i % 50 == 0 or i == count):
            print(f"  ✔ {i}/{count} images generated…")

    print(f"\n✅  Done! {count} images saved to: {out_dir.resolve()}")
    print("\n📊  Augmentation usage stats:")
    for name, cnt in sorted(aug_counter.items(), key=lambda x: -x[1]):
        bar = "█" * (cnt // max(1, count // 40))
        print(f"  {name:<14} {bar} {cnt}")
    print()


# ─────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate an augmented image dataset from a single source image."
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to the source image (e.g. cat.jpg)"
    )
    parser.add_argument(
        "--output", "-o", default="./augmented_dataset",
        help="Output directory (default: ./augmented_dataset)"
    )
    parser.add_argument(
        "--count", "-n", type=int, default=300,
        help="Number of augmented images to generate (default: 300)"
    )
    parser.add_argument(
        "--min-augs", type=int, default=1,
        help="Min augmentations per image (default: 1)"
    )
    parser.add_argument(
        "--max-augs", type=int, default=4,
        help="Max augmentations per image (default: 4)"
    )
    parser.add_argument(
        "--format", default="JPEG", choices=["JPEG", "PNG", "WEBP"],
        help="Output image format (default: JPEG)"
    )
    parser.add_argument(
        "--quality", type=int, default=90,
        help="JPEG quality 1-95 (default: 90)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)

    generate_dataset(
        source_path=args.input,
        output_dir=args.output,
        count=args.count,
        min_augs=args.min_augs,
        max_augs=args.max_augs,
        output_format=args.format,
        quality=args.quality,
    )
