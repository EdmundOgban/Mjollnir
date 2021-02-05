import unicodedata
from itertools import chain


def regflag(regcode):
    regionals_list = sorted(regionals)
    return ''.join(regionals_list[ord(c) - ord('A')] for c in regcode)

regionals = {chr(o) for o in range(0x1F1E6, 0x1F1FF+1)}

# List of codepoints that make up a regional flag
flags = {regflag(rc) for rc in (
    "AC AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH "
    "BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM "
    "CN CO CP CR CU CV CW CX CY CZ DE DG DJ DK DM DO DZ EA EC EE EG EH ER ES "
    "ET EU FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT "
    "GU GW GY HK HM HN HR HT HU IC ID IE IL IM IN IO IQ IR IS IT JE JM JO JP "
    "KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC "
    "MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE "
    "NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY "
    "QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV "
    "SX SY SZ TA TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM UN "
    "US UY UZ VA VC VE VG VI VN VU WF WS XK YE YT ZA ZM ZW".split()
)}

skintones = {chr(o) for o in range(0x1F3FB, 0x1F3FF+1)}

# List of emojis that accept skintones
skinnables = {chr(o) for o in (
    0x261D, 0x26F9, 0x270A, 0x270B, 0x270C, 0x270D,
    0x1F385, 0x1F3C2, 0x1F3C3, 0x1F3C4, 0x1F3C7, 0x1F3CA, 0x1F3CB, 0x1F3CC,
    0x1F442, 0x1F443, 0x1F446, 0x1F447, 0x1F448, 0x1F449, 0x1F44A, 0x1F44B,
    0x1F44C, 0x1F44D, 0x1F44E, 0x1F44F, 0x1F450, 0x1F466, 0x1F467, 0x1F468,
    0x1F469, 0x1F46B, 0x1F46C, 0x1F46D, 0x1F46E, 0x1F470, 0x1F471, 0x1F472,
    0x1F473, 0x1F474, 0x1F475, 0x1F476, 0x1F477, 0x1F478, 0x1F47C, 0x1F481,
    0x1F482, 0x1F483, 0x1F485, 0x1F486, 0x1F487, 0x1F48F, 0x1F491, 0x1F4AA,
    0x1F574, 0x1F575, 0x1F57A, 0x1F590, 0x1F595, 0x1F596, 0x1F645, 0x1F646,
    0x1F647, 0x1F64B, 0x1F64C, 0x1F64D, 0x1F64E, 0x1F64F, 0x1F6A3, 0x1F6B4,
    0x1F6B5, 0x1F6B6, 0x1F6C0, 0x1F6CC, 0x1F90C, 0x1F90F, 0x1F918, 0x1F919,
    0x1F91A, 0x1F91B, 0x1F91C, 0x1F91E, 0x1F91F, 0x1F926, 0x1F930, 0x1F931,
    0x1F932, 0x1F933, 0x1F934, 0x1F935, 0x1F936, 0x1F937, 0x1F938, 0x1F939,
    0x1F93D, 0x1F93E, 0x1F977, 0x1F9B5, 0x1F9B6, 0x1F9B8, 0x1F9B9, 0x1F9BB,
    0x1F9CD, 0x1F9CE, 0x1F9CF, 0x1F9D1, 0x1F9D2, 0x1F9D3, 0x1F9D4, 0x1F9D5,
    0x1F9D6, 0x1F9D7, 0x1F9D8, 0x1F9D9, 0x1F9DA, 0x1F9DB, 0x1F9DC, 0x1F9DD
)}

# Dropped in favor of unicodedata.category
# combinings = {chr(o) for o in chain(
#     range(0x0300, 0x036F+1), # Combining Diacritical Marks
#     range(0x1AB0, 0x1AFF+1), # Combining Diacritical Marks Extended
#     range(0x1DC0, 0x1DFF+1), # Combining Diacritical Marks Supplement
#     range(0x20D0, 0x20FF+1), # Combining Diacritical Marks for Symbols
#     range(0xFE20, 0xFE2F+1), # Combining Half Marks
#     (0x0488, 0x0489),        # 0x20DD?
#     range(0xA670, 0xA672+1)  # Combining Cyrillic Numerical Signs
# )}

variations = {chr(o) for o in chain(
    range(0xFE00 , 0xFE0F+1), # Variation Selectors
    range(0xE0100, 0xE01EF+1) # Variation Selectors Supplement
)}

zerowidth_joiner = "\u200d"


def is_breakable(cp, prevcp, checkflags=True):
    cp_combining = unicodedata.category(cp).startswith("M")
    return not (
            # combining codepoint follows an ascii character
            (ord(prevcp) < 128 and cp_combining)
            # is a combining codepoint
            or cp_combining
            # is a variation codepoint
            or cp in variations
            # is a ZWJ or preceded by it
            or zerowidth_joiner in (cp, prevcp)
            # is a skinned emoji
            or (prevcp in skinnables and cp in skintones)
            # is a flag
            # FIXME: flags should be handled with lookahead
            or (checkflags and prevcp + cp in flags)
    )


class UTF8Chunker:
    def __init__(self, stream=None):
        if stream is not None:
            self.set_stream(stream)

    def set_stream(self, stream):
        if not isinstance(stream, str):
            raise ValueError("Nope")

        self.stream = stream
        self.stream_len = len(stream)
        self.reset()

    def next_chunk(self, chunksize):
        while self.cp_pos < self.stream_len:
            cp = self.stream[self.cp_pos]
            c = cp.encode()
            c_size = len(c)
            if self.bin_pos + c_size > chunksize:
                return self._handle_overflow(cp, c, chunksize)
            else:
                self.out += c
                self.bin_pos += c_size
                self.cp_pos += 1

        if self.out and not self.finished:
            self.finished = True
            return self.out

    def chunkify(self, chunksize):
        if not self.stream:
            return

        self.reset()
        while not self.finished:
            yield self.next_chunk(chunksize)

    def reset(self):
        self.out = bytearray()
        self.finished = False
        self.cp_pos = 0
        self.bin_pos = 0

    def _seek_to_breakable(self, cp):
        cp_pos = self.cp_pos
        bin_pos = self.bin_pos

        while bin_pos > 0:
            prevcp = self.stream[cp_pos - 1]
            if is_breakable(cp, prevcp):
                # Update self.cp_pos only if breakable
                self.cp_pos = cp_pos
                return bin_pos
            else:
                bin_pos -= len(prevcp.encode())
                cp_pos -= 1
                cp = self.stream[cp_pos]

        return None

    def _handle_overflow(self, cp, c, chunksize):
        if c[0] & 0x80 == 0:
            # No utf-8 here, yield whole chunk
            bytecnt = chunksize
        else:
            bytecnt = self._seek_to_breakable(cp)
            # Chunk is unbreakable, yield it whole
            if bytecnt is None:
                bytecnt = len(self.out)

        chunk = self.out[:bytecnt]
        self.out.clear()
        self.bin_pos = 0
        return chunk


def split(stream):
    separated = []
    if len(stream) == 0:
        return separated

    start = 0
    end = 1
    prevcp = stream[0]

    while end < len(stream):
        cp = stream[end]
        if is_breakable(cp, prevcp, checkflags=False):
            if prevcp + cp in flags:
                end += 1

            separated.append(stream[start:end])
            start = end

        if end < len(stream):
            prevcp = stream[end]
            end += 1

    if stream[start:end]:
        separated.append(stream[start:end])

    return separated
