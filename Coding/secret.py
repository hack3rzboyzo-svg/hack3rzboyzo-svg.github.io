# image_secret_language_auto.py
# Automatically finds files on your computer

from PIL import Image
import base64
import os
from pathlib import Path

# =========================
# SECRET LANGUAGE SETTINGS
# =========================

ZERO = "△"
ONE = "◉"

# =========================
# SEARCH FOR FILE
# =========================

def find_file(filename):
    home = Path.home()

    common_folders = [
        home / "Desktop",
        home / "Downloads",
        home / "Documents",
        home / "Pictures",
        Path.cwd()
    ]

    for folder in common_folders:
        try:
            for path in folder.rglob(filename):
                return str(path)
        except:
            pass

    return None

# =========================
# ENCODE IMAGE
# =========================

def image_to_secret_language(image_name, output_text_file):
    image_path = find_file(image_name)

    if not image_path:
        print(f"[!] Could not find image: {image_name}")
        return

    print(f"[+] Found image at: {image_path}")

    with open(image_path, "rb") as img_file:
        image_bytes = img_file.read()

    b64_data = base64.b64encode(image_bytes)

    binary_string = ''.join(format(byte, '08b') for byte in b64_data)

    secret_text = binary_string.replace('0', ZERO).replace('1', ONE)

    output_path = Path.cwd() / output_text_file

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(secret_text)

    print(f"[+] Encoded successfully!")
    print(f"[+] Saved text file to: {output_path}")

# =========================
# DECODE SECRET LANGUAGE
# =========================

def secret_language_to_image(secret_filename, output_image):
    secret_path = find_file(secret_filename)

    if not secret_path:
        print(f"[!] Could not find text file: {secret_filename}")
        return

    print(f"[+] Found secret file at: {secret_path}")

    with open(secret_path, "r", encoding="utf-8") as file:
        secret_text = file.read()

    binary_string = secret_text.replace(ZERO, '0').replace(ONE, '1')

    byte_chunks = [
        binary_string[i:i+8]
        for i in range(0, len(binary_string), 8)
    ]

    byte_data = bytes(
        int(chunk, 2)
        for chunk in byte_chunks
        if len(chunk) == 8
    )

    image_bytes = base64.b64decode(byte_data)

    output_path = Path.cwd() / output_image

    with open(output_path, "wb") as img_file:
        img_file.write(image_bytes)

    print(f"[+] Image restored!")
    print(f"[+] Saved image to: {output_path}")

# =========================
# MENU
# =========================

def main():
    print("=== IMAGE SECRET LANGUAGE ===")
    print("1. Encode Image")
    print("2. Decode Secret Language")

    choice = input("Choose option: ")

    if choice == "1":
        image_name = input("Enter image filename (example: cat.png): ")
        output_text = input("Output text file name: ")

        image_to_secret_language(image_name, output_text)

    elif choice == "2":
        secret_file = input("Enter secret text filename: ")
        output_image = input("Output image filename: ")

        secret_language_to_image(secret_file, output_image)

    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()