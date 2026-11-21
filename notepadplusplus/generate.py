"""Generate Lichen.xml for Notepad++ by recolouring a bundled Notepad++ theme with the Lichen palette.

Usage: python generate.py [base-theme.xml] [output.xml]
"""

import html
import re
import sys
from pathlib import Path

BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Program Files\Notepad++\themes\DarkModeDefault.xml")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).with_name("Lichen.xml")

BG = "0b0d0c"
BG_RAISED = "101312"
BG_CHROME = "080a09"

BOLD, ITALIC, UNDERLINE = 1, 2, 4


def blend(fg: str, alpha: float, bg: str = BG) -> str:
    """Return fg composited over bg at the given alpha, since Notepad++ colours have no alpha channel."""
    f = [int(fg[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(bg[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(bc + (fc - bc) * alpha):02x}" for fc, bc in zip(f, b))


# Role -> (foreground, fontStyle). Colours come from themes/lichen-color-theme.json.
ROLES = {
    "default": ("6c7a70", 0),
    "comment": ("3c4641", 0),
    "punct": ("5b6761", 0),
    "keyword": ("458e72", ITALIC),
    "string": ("9e7b44", 0),
    "escape": ("a36584", 0),
    "number": ("8e854c", 0),
    "func_decl": ("5d9b83", 0),
    "func_call": ("60897b", ITALIC),
    "type": ("518691", 0),
    "type_word": ("518691", ITALIC),
    "param": ("7b73a5", 0),
    "property": ("668357", 0),
    "namespace": ("718079", 0),
    "decorator": ("a36584", ITALIC),
    "tag": ("518691", 0),
    "error": ("b45959", 0),
    "heading": ("458e72", BOLD),
    "strong": ("7c8783", BOLD),
    "italic": ("6c7a70", ITALIC),
    "link": ("518691", UNDERLINE),
    "underline": ("6c7a70", UNDERLINE),
    "quote": ("515c57", ITALIC),
    "added": ("458e72", 0),
    "deleted": ("b45959", 0),
    "changed": ("9e7b44", 0),
    "dim": ("515c57", 0),
}

ANSI = {
    "BLACK": "101312", "RED": "b45959", "GREEN": "458e72", "BROWN": "9e7b44", "YELLOW": "9c9254",
    "BLUE": "518691", "MAGENTA": "7b73a5", "CYAN": "668357", "GRAY": "6c7a70", "DARK GRAY": "3c4641",
    "BRIGHT RED": "c66868", "BRIGHT GREEN": "4c9d7e", "BRIGHT BLUE": "58919c",
    "BRIGHT MAGENTA": "8a83af", "BRIGHT CYAN": "729262", "WHITE": "7c8783",
}

# First matching pattern wins, so specific names go before the broad keyword/string catch-alls.
RULES = [
    (r"^(DEFAULT|DEFAULT STYLE|DEFAULT TEXT STYLE|IDENTIFIERS?|WHITE ?SPACE|TEXT|ANY OTHER TEXT|NAME)$", "default"),
    (r"^DIFF ADDITION$|^ADDED", "added"),
    (r"^DIFF DELETION$|^DELETED$|^REMOVED", "deleted"),
    (r"^DIFF CHANGED$", "changed"),
    (r"^DIFF MESSAGE$", "namespace"),
    (r"^(SEARCH HEADER)$", "heading"),
    (r"^FILE HEADER$", "type"),
    (r"^LINE NUMBER$", "dim"),
    (r"^HIT WORD$", "string"),
    (r"^CLASS NAME", "type"),
    (r"^EM2", "underline"),
    (r"^FILE \{", "link"),
    (r"ERROR|ILLEGAL|GARBAGE|WRONG|\bEOL\b|NOT CLOSED|UNKNOWN|BAD STRING|TOO MANY|IMPORTANT", "error"),
    (r"DOC KEYWORD|DOCUMENTATION (MACRO|HELPER)", "keyword"),
    (r"COMMENT|^POD|^DSC ", "comment"),
    (r"^VAR IN |STRING VAR|^INSTANCE VAR|^CLASS VAR", "default"),
    (r"ESCAPE|REGEX|SUBSTITUTION|SPECIAL CHAR|FORMAT IDENTIFIER|^ENTITY$|PLACEHOLDER", "escape"),
    (r"^H[1-6]$|^HEADER$|SECTION", "heading"),
    (r"^STRONG|^BOLD", "strong"),
    (r"^EM1|^ITALIC", "italic"),
    (r"^BLOCKQUOTE$", "quote"),
    (r"^LINK$|^URL|^URI$|^EMAIL|COMPACT IRI", "link"),
    (r"^CODE|^CODEBLOCK$|^BACKTICKS$|^MATH", "string"),
    (r"STRING|CHAR|VERBATIM|HEREDOC|^HERE |TRIPLE|QUOTE|CDATA|^RAW|^LITERAL|^F TRIPLE|^MONEY", "string"),
    (r"NUMBER|NUMERIC|^HEX|^BINARY|^BIN|^BOOL$|^NIL$|CONSTANT|^DATE|^TIME|^ATOM|^PAIR|^TUPLE|^VALUE", "number"),
    (r"DECORATOR|ANNOTATION|MACRO|PREPROC|^DIRECTIVE|IFDEF|IF DEFINE|PRAGMA|^PREWORD|^POSTPROC", "decorator"),
    (r"TAG|^SGML|^XMLSTART$|^XMLEND$", "tag"),
    (r"^PARAM|PARAMETER|ARGUMENT|POSITIONAL", "param"),
    (r"ATTRIBUTE|PROPERTY|^KEY$|^KEY |^PROPERTY|^COL NAME|^REGISTER|PSEUDO|SELECTOR|^MEDIA", "property"),
    (r"DEFINITION|^DEF NAME|^FUNC NAME|^FUNCTION NAME|CLASS NAME|^PROTOTYPE", "func_decl"),
    (r"FUNC|METHOD|CMDLET|CALLABLE|^COMMAND|^TK COMMAND|^STD OPERATOR|BUILT-?IN|BUILIN|DLL|CORE API|PLUGIN", "func_call"),
    (r"^TYPE WORD$|^TYPES?$|DATA ?TYPE|^STD TYPE|^TYPEDEF|^VALUE TYPE|^CLASS$|^RECTYPE", "type_word"),
    (r"MODULE|NAMESPACE|PACKAGE|^IMPORT|^ALIAS", "namespace"),
    (r"^LABEL|REFERENCE", "namespace"),
    (r"OPERATOR|DELIMITER|SYMBOL|BRACE|^PAREN|ASSIGN|QUESTION|ASTERISK|DIVIS|^INFIX|CONTINUATION", "punct"),
    (r"VARIABLE|^VAR$|SCALAR|^ARRAY$|^HASH$|^GLOBAL|^INSTANCE$|^IDENTIFIER\d", "default"),
    (r"^SELF$|^SUPER$", "keyword"),
    (r"KEYWORD|WORD|INSTR|STATEMENT|RESERVED|CONTROL|RETURN|MODIFIER|OPCODE|^USER|SPECIAL|^PREDEFINED|"
     r"DECLARATION|^FILTER|^TARGET|^OPTION|^EVENT|^GRAMMAR|^QUALIFIER|^PREDECLARED", "keyword"),
]

# Styles whose background carries meaning; everything else gets the editor background.
LEXER_BG = {
    ("searchResult", "Hit Word"): blend("9e7b44", 0.25),
    ("searchResult", "Current line background colour"): blend("31925d", 0x2a / 255),
}

line_highlight = blend("31925d", 0x2a / 255)

GLOBAL = {
    "Default Style": dict(fgColor="6c7a70", bgColor=BG),
    "Indent guideline style": dict(fgColor="1a1e1d", bgColor=BG),
    "Brace highlight style": dict(fgColor="7c8783", bgColor="232827", fontStyle="1"),
    "Bad brace colour": dict(fgColor="b45959", bgColor=BG),
    "Current line background colour": dict(bgColor=line_highlight),
    "Selected text colour": dict(bgColor="1b2d26", fgColor="7c8783"),
    "Multi-selected text color": dict(bgColor="1b2d26"),
    "Caret colour": dict(fgColor="458e72"),
    "Multi-edit carets color": dict(fgColor="5d9b83"),
    "Edge colour": dict(fgColor="1a1e1d"),
    "Line number margin": dict(fgColor="383f3b", bgColor=BG),
    "Bookmark margin": dict(bgColor=BG),
    "Change History margin": dict(bgColor=BG),
    "Change History modified": dict(fgColor="9e7b44", bgColor="9e7b44"),
    "Change History revert modified": dict(fgColor="8e854c", bgColor="8e854c"),
    "Change History revert origin": dict(fgColor="518691", bgColor="518691"),
    "Change History saved": dict(fgColor="458e72", bgColor="458e72"),
    "Fold": dict(fgColor="3c4641", bgColor=BG),
    "Fold active": dict(fgColor="458e72"),
    "Fold margin": dict(fgColor=BG, bgColor=BG),
    "White space symbol": dict(fgColor="232827"),
    "Smart Highlighting": dict(bgColor=blend("3a4442", 0x99 / 255)),
    "Find Mark Style": dict(bgColor="3d3220"),
    "Find status: Not found": dict(fgColor="b45959"),
    "Find status: Message": dict(fgColor="518691"),
    "Find status: Search end reached": dict(fgColor="458e72"),
    "Mark Style 1": dict(bgColor=blend("458e72", 0.3)),
    "Mark Style 2": dict(bgColor=blend("9e7b44", 0.3)),
    "Mark Style 3": dict(bgColor=blend("b45959", 0.3)),
    "Mark Style 4": dict(bgColor=blend("518691", 0.3)),
    "Mark Style 5": dict(bgColor=blend("7b73a5", 0.3)),
    "Incremental highlight all": dict(bgColor="3d3220"),
    "Tags match highlighting": dict(bgColor="232827"),
    "Tags attribute": dict(bgColor="1a1f1d"),
    "Active tab focused indicator": dict(fgColor="458e72"),
    "Active tab unfocused indicator": dict(fgColor="2c5c48"),
    "Active tab text": dict(fgColor="7c8783"),
    "Inactive tabs": dict(fgColor="515c57", bgColor=BG_RAISED),
    "Tab color dark mode 1": dict(bgColor=blend("9e7b44", 0.35, BG_RAISED)),
    "Tab color dark mode 2": dict(bgColor=blend("458e72", 0.35, BG_RAISED)),
    "Tab color dark mode 3": dict(bgColor=blend("518691", 0.35, BG_RAISED)),
    "Tab color dark mode 4": dict(bgColor=blend("b45959", 0.35, BG_RAISED)),
    "Tab color dark mode 5": dict(bgColor=blend("7b73a5", 0.35, BG_RAISED)),
    "URL hovered": dict(fgColor="58919c"),
    "Document map": dict(fgColor="2c5c48", bgColor="1b2d26"),
    "EOL custom color": dict(fgColor="3c4641"),
    "Non-printing characters custom color": dict(fgColor="232827"),
    "Global override": dict(fgColor="6c7a70", bgColor=BG),
}


def role_for(name: str) -> tuple[str, int]:
    upper = name.upper()
    ansi = re.match(r"ANSI COLOR (.+)", upper)
    if ansi:
        return ANSI[ansi.group(1)], 0
    for pattern, role in RULES:
        if re.search(pattern, upper):
            return ROLES[role]
    return ROLES["default"]


def set_attr(line: str, attr: str, value: str) -> str:
    if f'{attr}="' in line:
        return re.sub(rf'{attr}="[^"]*"', f'{attr}="{value}"', line)
    return re.sub(r"\s*/?>", lambda m: f' {attr}="{value}"{m.group(0)}', line, count=1)


def main() -> None:
    out = []
    lexer = None
    for line in BASE.read_text(encoding="utf-8").splitlines():
        if m := re.search(r'<LexerType name="([^"]*)"', line):
            lexer = m.group(1)
        elif m := re.search(r'<WordsStyle name="([^"]*)"', line):
            name = html.unescape(m.group(1))
            bg = LEXER_BG.get((lexer, name), BG)
            if 'fgColor="' in line:
                fg, style = role_for(name)
                line = set_attr(line, "fgColor", fg)
                line = set_attr(line, "fontStyle", str(style))
            line = set_attr(line, "bgColor", bg)
        elif m := re.search(r'<WidgetStyle name="([^"]*)"', line):
            for attr, value in GLOBAL.get(html.unescape(m.group(1)), {}).items():
                line = set_attr(line, attr, value)
        out.append(line)

    text = "\n".join(out) + "\n"
    text = re.sub(r"<!--.*?-->\s*<NotepadPlus",
                  "<!--\nLichen for Notepad++. Generated by generate.py from " + BASE.name + ".\nLicense: GPL2 (base file)\n-->\n<NotepadPlus",
                  text, count=1, flags=re.S)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
