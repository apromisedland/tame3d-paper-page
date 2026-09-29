import shutil
from pathlib import Path

import pypdfium2 as pdfium


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "assets"


def main():
    DESTINATION.mkdir(exist_ok=True)
    copies = {
        "paper/Tame3D.pdf": "tame3d-paper.pdf",
    }
    for source, target in copies.items():
        shutil.copyfile(ROOT / source, DESTINATION / target)
    document = pdfium.PdfDocument(str(DESTINATION / "tame3d-paper.pdf"))
    crops = {
        "framework": (2, (0.174, 0.095, 0.831, 0.333)),
        "observation-shift": (6, (0.175, 0.098, 0.820, 0.285)),
    }
    for name, (page_index, bounds) in crops.items():
        page = document[page_index]
        bitmap = page.render(scale=4)
        rendered = bitmap.to_pil()
        box = tuple(round(value * (rendered.width if index % 2 == 0 else rendered.height)) for index, value in enumerate(bounds))
        cropped = rendered.crop(box)
        cropped.save(DESTINATION / f"{name}.png", optimize=True)
        cropped.save(DESTINATION / f"{name}.webp", quality=92, method=6)
        print(f"{name}: {cropped.width} x {cropped.height}")
        page.close()
    document.close()
    print("Prepared the unchanged public PDF and original figure crops.")


if __name__ == "__main__":
    main()
