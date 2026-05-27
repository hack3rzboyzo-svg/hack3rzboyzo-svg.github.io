from pathlib import Path
from PIL import Image
import sys

# filename as you have it
imageName = "ab-twill-baggy-cargo-pant-tan-front-10002879-1347307216.jpeg"

# resolve path relative to the script file
script_dir = Path(__file__).resolve().parent
img_path = script_dir / imageName

# debug info
print("cwd:", Path.cwd())
print("script dir:", script_dir)
print("exists in script dir?:", img_path.exists())
print("files in script dir:", [p.name for p in script_dir.iterdir() if p.is_file()])

if not img_path.exists():
    print(f"Image not found at: {img_path}")
    sys.exit(1)

testImg = Image.open(img_path)
print("Opened image size:", testImg.size)

