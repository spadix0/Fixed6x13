from copy import deepcopy
from unicodedata import category


class Font:
    def __init__(self):
        self.glyphs = {}
        self.version = 0.0

    def __str__(self):
        name = getattr(self, 'fullname', '') \
            or getattr(self, 'family', '') \
            or 'BDF font'
        if ver := self.version:
            name += f' version={ver}'
        return f'{name} {len(self.glyphs)} glyphs'

    def calc_bbox(self):
        boxes = [ g.calc_bbox() for g in self.glyphs.values() ]
        return (
            min(r[0] for r in boxes),
            min(r[1] for r in boxes),
            max(r[2] for r in boxes),
            max(r[3] for r in boxes),
        )

    @staticmethod
    def char_combining(code):
        if code >= 0x20 and (cat := category(chr(code)).startswith('M')):
            return cat

    def set_glyph(self, glyph):
        try:
            key = chr(glyph.code)
        except:
            key = glyph.code
        self.glyphs[key] = glyph
        return glyph

    def add_glyph_uniart(self, code, img):
        glyph = Glyph.from_uniart(code, img)
        self.set_glyph(glyph)
        return glyph


class Glyph:
    def __init__(self, code=None, name=None):
        if isinstance(code, str):
            code = ord(code)
        self.code = code
        self.name = name
        self.bitmap = None
        self.contours = ()
        self.advance = 0

    def __str__(self):
        bbox = getattr(self, 'bbox', None) or self.calc_bbox()
        if bits := self.bitmap or '':
            bits = ' [' + ' '.join(f'{b:02x}' for b in bits) + ']'
        return f'[{self.code:04x}] {self.name}: {bbox}{self.advance:+}{bits}'

    @classmethod
    def from_uniart(cls, code, img):
        glyph = cls(code)

        img = img.split('\n')
        while not img[-1].strip():
            img.pop()
        while not img[0].strip():
            img.pop(0)

        x0 = img[0].index('▕') + 1
        x1 = img[0].index('▏')
        glyph.advance = x1 - x0
        xmin = min(x for row in img for x,c in enumerate(row) if c in '▀█▄')
        xmax = max(x for row in img for x,c in enumerate(row) if c in '▀█▄') + 1
        xmax = max(xmax, x1)
        width = xmax - xmin

        bmp = glyph.bitmap = []
        for y, row in enumerate(img):
            if row.lstrip().startswith('▔'):
                y0 = y
            bmp += [ 0, 0 ]
            row += ' '*width
            for c in row[xmin:xmax]:
                bmp[-2] <<= 1;  bmp[-1] <<= 1
                match c:
                    case '▀': bmp[-2] |= 1
                    case '▄': bmp[-1] |= 1
                    case '█': bmp[-2] |= 1;  bmp[-1] |= 1

        glyph.bbox = [
            xmin - x0, 2*(y0 - len(img)), xmax - x0, 2*y0
        ]
        return glyph

    def clone(self, code):
        glyph = deepcopy(self)
        if isinstance(code, str):
            code = ord(code)
        glyph.code = code
        return glyph

    def shift(self, dx, dy):
        assert self.bitmap
        assert not self.contours
        bbox = self.bbox
        bbox[0] += dx
        bbox[1] += dy
        bbox[2] += dx
        bbox[3] += dy
        return self

    def calc_bbox(self):
        if not (contours := self.contours):
            return (0, 0, 0, 0)
        else:
            return (
                min(p[0] for c in contours for p in c),
                min(p[1] for c in contours for p in c),
                max(p[0] for c in contours for p in c),
                max(p[1] for c in contours for p in c),
            )

    def combining(self):
        return Font.char_combining(self.code)

    # codes for special case glyphs
    NOTDEF = -1
    NULL = '\0'
    SPACE = ' '

Font.Glyph = Glyph
