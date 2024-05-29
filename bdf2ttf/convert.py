from math import floor
import unicodedata

from .font import Font, Glyph
from .bdf import BDFReader
from .ttf import TTFWriter


def bdf2ttf(bdf, mod=None):
    font = BDFReader().read(bdf)
    print(font)

    if mod and (apply := mod.apply_bitmaps):
        apply(font)

    # make big grid so chamfers disappear
    maxupm = 1<<13
    scale = maxupm // font.size

    for ch, glyph in font.glyphs.items():
        code = ord(ch) if isinstance(ch, str) else ch
        if glyph.code == code:
            vectorize_glyph(glyph, scale)

    clean_glyphs(font)

    scale_font(font, scale)

    font.bbox = font.calc_bbox()
    ttf = TTFWriter(font)
    ttf.head.lowestRecPPEM = font.size // scale

    # A font's filename must be composed as "<familyname>-<stylename>.ttf"
    # [aka, the postscript name]
    with open(f'{ttf.name.psname}.ttf', 'wb+') as out:
        ttf.write(out)

    # also make "proof sheet" of all characters in font
    with open(f'{ttf.name.psname} chars.txt', 'w') as out:
        dump_chars(font, out)


def clean_glyphs(font):
    glyphs = font.glyphs

    # fontbakery says this is deprecated
    glyphs.pop('\xad', None)

    # The first glyph (glyph index 0) must be the MISSING CHARACTER GLYPH.
    # This glyph must have a visible appearance and non-zero advance width.
    notdef = glyphs[Glyph.NOTDEF]
    assert notdef.contours
    assert notdef.advance > 0

    # The second glyph (glyph index 1) must be the NULL glyph. This glyph must
    # have no contours and zero advance width.
    if not (null := glyphs.get(Glyph.NULL)):
        null = glyphs[Glyph.NULL] = Glyph(ord(Glyph.NULL), '.null')
    assert not null.contours
    assert null.advance == 0

    space = glyphs[Glyph.SPACE]

    for ch, glyph in glyphs.items():
        code = ord(ch) if isinstance(ch, str) else ch
        if code > 0 and not glyph.contours:
            #print(f'empty: U+{code:04x}')
            glyphs[ch] = space

    # these codes are required to reference these glyphs
    for code in required_notdef:
        glyphs[chr(code)] = notdef
    for code in required_null:
        glyphs[chr(code)] = null
    for code in required_space:
        glyphs[chr(code)] = space


def dump_chars(font, out, cols=0x20):
    prev = -1
    codes = sorted(ord(c) if isinstance(c, str) else c for c in font.glyphs)
    for code in codes:
        if code >= 0x20:
            irow = code // cols
            jcol = code % cols
            if jcol == 0 or irow != prev // cols:
                if prev >= 0x20:
                    out.write('\n')
                codestr = f'U+{code:04x}'
                out.write(f'{codestr:8}    ')
                prev = irow*cols - 1

            ch = chr(code)
            if Font.char_combining(code):
                ch = '◌' + ch
            out.write(' '*2*(jcol - (prev+1)%cols) + ' ' + ch)
            prev = code

    out.write('\n')


def scale_font(font, scale):
    under = font.underline
    for i in range(len(under)):
        under[i] *= scale

    font.caret[1] *= scale
    font.ascent *= scale
    font.descent *= scale
    font.capheight *= scale
    font.xheight *= scale
    font.linegap *= scale
    if font.fixedpitch:
        font.fixedpitch *= scale
    font.size *= scale

    for ch, glyph in font.glyphs.items():
        code = ord(ch) if isinstance(ch, str) else ch
        if glyph.code == code:
            scale_glyph(glyph, scale)


def scale_glyph(glyph, scale):
    glyph.advance = round(glyph.advance * scale)
    if contours := glyph.contours:
        for c in contours:
            for i, p in enumerate(c):
                c[i] = [ round(p[0]*scale), round(p[1]*scale) ]


def vectorize_glyph(glyph, scale):
    if not glyph.bitmap:
        return

    bmp = [ 0, *(d<<1 for d in glyph.bitmap), 0 ]

    nudge = 1/scale
    x0, y0, x1, y1 = glyph.bbox
    del glyph.bbox
    w, h = x1-x0, y1-y0
    contours = glyph.contours = []

    def get4n(x, y):
        s = w+1 - x
        return (bmp[y]>>s & 3)<<2 | (bmp[y+1]>>s & 3)

    corners = {
        (x, y, *d): True	# sets suck
        for y in range(h + 1)
        for x in range(w + 1)
        for d in cornerdirs.get(get4n(x, y), ())
    }

    while corners:
        (x,y, dx,dy), _ = corners.popitem()
        ctr = []
        contours.append(ctr)

        # corners end up sorted bottom to top,
        # so we never have to chamfer final segment
        assert get4n(x, y) not in diagonal or dx < 0 or dy > 0

        while True:
            n4 = get4n(x, y)
            if n4 not in cornerdirs:
                pass
            elif n4 in internal:
                ctr.append((x, y))
                dx,dy = dy, -dx
            elif n4 not in diagonal or dx < 0 or dy > 0:
                ctr.append((x, y))
                dx,dy = -dy, dx
            else:
                # chamfer upper corners of diagonal intersections (only)
                # to avoid bogus errors about overlapping contours
                ctr.append((x - dx*nudge, y - dy*nudge))
                dx,dy = -dy, dx
                ctr.append((x + dx*nudge, y + dy*nudge))

            #print((x,y), (dx,dy))
            x += dx
            y += dy
            if ctr[0] == (x,y):
                break
            corners.pop((x,y, dx,dy), None)

        for i, (x, y) in enumerate(ctr):
            ctr[i] = [ x-1+x0, h-y+y0 ]

    if category := glyph.combining():
        # implement combining marks by hacking their position to overlay
        # previous glyph and clearing their advance.  this "works" but
        # it's hacky and generates some validation warnings...
        # FIXME reimplement combining marks using GPOS?
        adv = glyph.advance
        for ctr in contours:
            for p in ctr:
                p[0] -= adv

        if category != 'Mc':
            glyph.advance = 0
        else:
            # these are probably wrong (but we don't have any...)
            print('FIXME: Mc:', glyph)


R = (1,0)
D = (0,1)
U = (0,-1)
L = (-1,0)

cornerdirs = {
    # uudd
    # lrlr
    0b0001: (U,),	# outside corners
    0b0010: (R,),
    0b0100: (L,),
    0b1000: (D,),

    0b1110: (L,),	# inside corners
    0b1101: (U,),
    0b1011: (D,),
    0b0111: (R,),

    0b1001: (U, D),	# diagonal intersections (checkers)
    0b0110: (L, R),
}

internal = (0b1110, 0b1101, 0b1011, 0b0111)
diagonal = (0b1001, 0b0110)


# https://developer.apple.com/fonts/TrueType-Reference-Manual/RM07/appendixB.html

# The following character codes must be mapped to the first glyph
# (glyph index 0, MISSING CHARACTER GLYPH):
required_notdef = [
    0x0001,	# START OF HEADING
    0x0002,	# START OF TEXT
    0x0003,	# END OF TEXT
    0x0004,	# END OF TRANSMISSION
    0x0005,	# ENQUIRY
    0x0006,	# ACKNOWLEDGE
    0x0007,	# BELL
    0x000A,	# LINE FEED
    0x000B,	# VERTICAL TABULATION
    0x000C,	# FORM FEED
    0x000E,	# SHIFT OUT
    0x000F,	# SHIFT IN
    0x0010,	# DATA LINK ESCAPE
    0x0011,	# DEVICE CONTROL 1 (X-On)
    0x0012,	# DEVICE CONTROL 2
    0x0013,	# DEVICE CONTROL 3 (X-Off)
    0x0014,	# DEVICE CONTROL 4
    0x0015,	# NEGATIVE ACKNOWLEDGE
    0x0016,	# SYNCHRONOUS IDLE
    0x0017,	# END OF TRANSMISSION BLOCK
    0x0018,	# CANCEL
    0x0019,	# END OF MEDIUM
    0x001A,	# SUBSTITUTE
    0x001B,	# ESCAPE
    0x001C,	# FILE SEPARATOR
    0x001E,	# RECORD SEPARATOR
    0x001F,	# UNIT SEPARATOR
    0x007F,	# DELETE
]

# The following characters must map to the second glyph
# (glyph index 1, the NULL glyph):
required_null = [
    0x0000,	# NULL
    0x0008,	# BACKSPACE
    #0x000D,	# CARRIAGE RETURN (in a right-to-left font)
    0x001D,	# GROUP SEPARATOR
]

# Each of the following characters must map to a glyph with no contours and
# positive advance width:
required_space = [
    0x0009,	# HORIZONTAL TABULATION
    0x000D,	# CARRIAGE RETURN (in a left-to-right font)
    0x0020,	# SPACE
    0x00A0,	# NO-BREAK SPACE
]
