import re

FG_RE = "\x03(\d{1,2})"
BG_RE = "(?:,(\d{1,2}))?"
REST_RE = "([^\x03]*)"
COLOR_RE = re.compile("{}{}{}|{}".format(FG_RE, BG_RE, REST_RE, REST_RE))
BOLD_RE = re.compile("\x02([^\x02]+)\x02?")
UNDERLINE_RE = re.compile("\x1f([^\x1f]+)\x1f?")
REVERSE_RE = re.compile("\x16([^\x16]+)\x16?")
VT100_FGCOLOR = {
    0: 97,
    1: 30,
    2: 34,
    3: 32,
    4: 91,
    5: 31,
    6: 35,
    7: 39,
    8: 93,
    9: 92,
    10: 94,
    11: 96,
    12: 34,
    13: 95,
    14: 90,
    15: 37
}


def colorize(text):
    out = []

    for fg, bg, colortext, rest in COLOR_RE.findall(text.strip("\x1B")):
        for c in colortext:
            colors = ""
            if fg:
                colors += str(VT100_FGCOLOR.get(int(fg), ''))

            if bg:
                colors += ";{}".format(VT100_FGCOLOR.get(int(bg)) + 10)

            if colors:
                out.append(f"\x1B[{colors}m{c}\x1B[39;49m")
            else:
                out.append(c)

        if rest:
            out.append(rest)

    text = "".join(out)
    # Bold is giving problems. Go figure ...
    # text = BOLD_RE.sub(f"\x1B[1m\\1\x1B[21m", text)
    # ... just strip it
    text = BOLD_RE.sub(r"\1", text)
    text = UNDERLINE_RE.sub(f"\x1B[4m\\1\x1B[24m", text)
    text = REVERSE_RE.sub(f"\x1B[7m\\1\x1B[27m", text)
    text = text.replace("\x0F", "\x1B[0m")

    return text
