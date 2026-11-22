"""Generate the Lichen file icon theme: extension labels drawn as Iosevka Medium capitals, tinted by file category.

Usage: python generate.py --font Iosevka-Medium.ttf [--preview preview.html]

Writes icons/svg/*.svg and themes/lichen-icon-theme.json. Edit CATEGORIES, EXTENSIONS and FILE_NAMES, then rerun.
Needs fontTools (pip install fonttools) and Iosevka-Medium.ttf from https://github.com/be5invis/Iosevka/releases.
"""

import json
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
SVG_DIR = ROOT / "icons" / "svg"
THEME = ROOT / "themes" / "lichen-icon-theme.json"

BG = "101312"
DIM = 0.25

FOLDER_COLOUR = "515c57"
DEFAULT_COLOUR = "3c4641"

# Label cap height, baseline and maximum ink width in 16x16 icon pixels.
CAP_HEIGHT = 7.7
BASELINE = (16 + CAP_HEIGHT) / 2
MAX_WIDTH = 15

# Category -> base colour from themes/lichen-color-theme.json, dimmed by DIM toward BG.
CATEGORIES = {
    "code": "458e72",
    "markup": "7b73a5",
    "config": "9e7b44",
    "docs": "668357",
    "data": "518691",
    "script": "8e854c",
    "binary": "515c57",
    "attention": "b45959",
}

# Extension -> (category, label). A label of None means the extension itself.
EXTENSIONS = {
    **{e: ("code", None) for e in "js mjs cjs ts tsx jsx py rs go c h cpp hpp cs kt rb php lua".split()},
    "java": ("code", "jav"),
    "reds": ("code", "rds"),
    "swift": ("code", "swf"),
    "mts": ("code", "ts"),
    "cts": ("code", "ts"),
    "pyw": ("code", "py"),
    **{e: ("markup", None) for e in "htm xml svg css vue".split()},
    "html": ("markup", "htm"),
    "scss": ("markup", "scs"),
    "less": ("markup", "lss"),
    **{e: ("config", None) for e in "ini cfg env yml".split()},
    "json": ("config", "{}"),
    "jsonc": ("config", "{}"),
    "json5": ("config", "{}"),
    "yaml": ("config", "yml"),
    "toml": ("config", "tml"),
    "conf": ("config", "cfg"),
    **{e: ("docs", None) for e in "md txt rst log".split()},
    "markdown": ("docs", "md"),
    **{e: ("data", None) for e in "csv tsv sql db".split()},
    "sqlite": ("data", "db"),
    **{e: ("script", None) for e in "sh bat cmd ps1".split()},
    "bash": ("script", "sh"),
    "psm1": ("script", "ps1"),
    "psd1": ("script", "ps1"),
    **{e: ("binary", None) for e in "png jpg gif ico exe dll zip".split()},
    "jpeg": ("binary", "jpg"),
    "webp": ("binary", "wbp"),
    "vsix": ("binary", "vsx"),
    **{e: ("attention", None) for e in "pem key".split()},
    "lock": ("attention", "lck"),
}

# Lowercase file name -> (category, label). VS Code matches these before extensions.
FILE_NAMES = {
    ".editorconfig": ("config", "cfg"),
    ".env": ("config", "env"),
    "makefile": ("script", "mk"),
    "dockerfile": ("script", "dkr"),
    ".gitignore": ("binary", "git"),
    ".gitattributes": ("binary", "git"),
    ".gitmodules": ("binary", "git"),
    "license": ("attention", "lic"),
    "license.md": ("attention", "lic"),
    "license.txt": ("attention", "lic"),
    "package-lock.json": ("attention", "lck"),
}

FOLDER = "M1.5 3.5h4l1.5 1.5h7.5v8.5h-13z"
FOLDER_OPEN = "M1.5 13.5v-10h4l1.5 1.5h6v2.5M1.5 13.5l2-6h11.5l-2 6z"
DASH = "M6.5 8.5h3"


def blend(fg: str, amount: float, bg: str = BG) -> str:
    """Return fg moved toward bg by amount, where 0 keeps fg and 1 gives bg."""
    f = [int(fg[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(bg[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(fc + (bc - fc) * amount):02x}" for fc, bc in zip(f, b))


def number(x: float) -> str:
    """Return x with at most 2 decimals and no trailing zeros."""
    return f"{x:.2f}".rstrip("0").rstrip(".")


def label_svg(font: TTFont, label: str, colour: str) -> str:
    """Return a 16x16 SVG with label set in font as capitals, centred on its ink bounds."""
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = CAP_HEIGHT / font["OS/2"].sCapHeight
    names = [cmap[ord(ch)] for ch in label.upper()]

    bounds = BoundsPen(glyphs)
    x = 0
    for name in names:
        glyphs[name].draw(TransformPen(bounds, (1, 0, 0, 1, x, 0)))
        x += glyphs[name].width
    left, _, right, _ = bounds.bounds
    width = (right - left) * scale
    if width > MAX_WIDTH:
        raise ValueError(f"label {label!r} is {width:.1f}px wide, over {MAX_WIDTH}px")

    pen = SVGPathPen(glyphs, ntos=number)
    offset = (16 - width) / 2 - left * scale
    x = 0
    for name in names:
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, offset + x * scale, BASELINE)))
        x += glyphs[name].width
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
            f'<path fill="#{colour}" d="{pen.getCommands()}"/></svg>\n')


def stroke_svg(d: str, colour: str) -> str:
    """Return a 16x16 SVG stroking path d with a 1px round-jointed line."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
            f'<path fill="none" stroke="#{colour}" stroke-linecap="round" stroke-linejoin="round" d="{d}"/></svg>\n')


def icon_name(label: str) -> str:
    """Return a file-safe icon id for label, hex-escaping anything that isn't alphanumeric."""
    return "".join(ch if ch.isalnum() else f"_{ord(ch):x}" for ch in label)


def main() -> None:
    args = sys.argv[1:]
    if "--font" not in args:
        sys.exit(__doc__)
    font = TTFont(args[args.index("--font") + 1])
    preview = Path(args[args.index("--preview") + 1]) if "--preview" in args else None

    SVG_DIR.mkdir(parents=True, exist_ok=True)
    for old in SVG_DIR.glob("*.svg"):
        old.unlink()

    svgs = {
        "_file": stroke_svg(DASH, DEFAULT_COLOUR),
        "_folder": stroke_svg(FOLDER, FOLDER_COLOUR),
        "_folder_open": stroke_svg(FOLDER_OPEN, FOLDER_COLOUR),
    }
    label_category = {}

    def icon_id(key: str, category: str, label: str | None) -> str:
        """Return the icon id for label in category, adding its SVG on first use."""
        label = label or key
        if label_category.setdefault(label, category) != category:
            raise ValueError(f"label {label!r} is used by both {label_category[label]} and {category}")
        name = icon_name(label)
        if name not in svgs:
            svgs[name] = label_svg(font, label, blend(CATEGORIES[category], DIM))
        return name

    extensions = {ext: icon_id(ext, *spec) for ext, spec in EXTENSIONS.items()}
    file_names = {name: icon_id(name, *spec) for name, spec in FILE_NAMES.items()}

    for name, svg in svgs.items():
        (SVG_DIR / f"{name}.svg").write_text(svg, encoding="utf-8")

    theme = {
        "iconDefinitions": {name: {"iconPath": f"../icons/svg/{name}.svg"} for name in sorted(svgs)},
        "file": "_file",
        "folder": "_folder",
        "folderExpanded": "_folder_open",
        "rootFolder": "_folder",
        "rootFolderExpanded": "_folder_open",
        "fileExtensions": extensions,
        "fileNames": file_names,
    }
    THEME.write_text(json.dumps(theme, indent="\t") + "\n", encoding="utf-8")
    print(f"{len(svgs)} icons, {len(extensions)} extensions, {len(file_names)} file names")

    if preview:
        rows = ["src", "node_modules"] + [f"example.{e}" for e in EXTENSIONS] + list(FILE_NAMES) + ["unknown.xyz"]
        items = []
        for name in rows:
            if "." not in name:
                icon = file_names.get(name, "_folder_open" if name == "src" else "_folder")
            else:
                icon = file_names.get(name) or extensions.get(name.rsplit(".", 1)[1], "_file")
            uri = (SVG_DIR / f"{icon}.svg").as_uri()
            items.append(f'<div><img src="{uri}" width="16" height="16"><span>{name}</span></div>')
        preview.write_text(
            "<!doctype html><style>body{background:#101312;color:#5b6761;font:13px 'Segoe UI',sans-serif;"
            "columns:4;padding:12px}div{display:flex;align-items:center;gap:6px;height:22px}</style>"
            f"<body>{''.join(items)}</body>\n",
            encoding="utf-8")
        print(f"preview: {preview}")


if __name__ == "__main__":
    main()
