from math import ceil

from .font import Font, Glyph


def _intlist(s):
    return [ int(v) for v in s.split() ]

def _floatlist(s):
    return [ float(v) for v in s.split() ]

def _none(s):
    return None


class BDFReader:
    handlers = {
        'STARTFONT': float,
        'ENDFONT': _none,
        'CONTENTVERSION': int,
        'SIZE': _floatlist,
        'FONTBOUNDINGBOX': _intlist,
        'METRICSET': int,
        'CHARS': _none,
        'ENCODING': int,
        'SWIDTH': _intlist,
        'DWIDTH': _intlist,
        'SWIDTH1': _intlist,
        'DWIDTH1': _intlist,
        'VVECTOR': _intlist,
        'BBX': _intlist,
    }

    def __init__(self, bdf=None):
        self.props = {}
        self.info = {
            'PROPERTIES': self.props,
        }
        self.chars = []

        if bdf is not None:
            self.read(bdf)

    def read(self, bdf):
        self._iter = iter(bdf)
        self._parse_file()
        return self._grok_font()

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            line = next(self._iter).strip()
            if not line:
                continue

            kv = line.split(maxsplit=1)
            if len(kv) < 2:
                kv.append('')
            else:
                assert kv[1] == kv[1].strip()
            return kv

    def _parse_file(self):
        for k, v in self:
            match k:
                case 'STARTCHAR':
                    self._parse_char(v)
                case 'STARTPROPERTIES':
                    self._parse_props()
                case _:
                    self._parse_kvp(self.info, k, v)

    def _parse_props(self):
        for k, v in self:
            if k == 'ENDPROPERTIES':
                return
            else:
                self._parse_kvp(self.props, k, v)

    def _parse_char(self, name):
        ch = {
            'CHAR': name,
        }
        self.chars.append(ch)

        for k, v in self:
            match k:
                case 'BITMAP':
                    self._parse_bitmap(ch)
                case 'ENDCHAR':
                    return
                case _:
                    self._parse_kvp(ch, k, v)

    def _parse_bitmap(self, ch):
        w, h = ch['BBX'][0:2]
        s = ((w + 7) >> 3 << 3) - w
        bmp = ch['BITMAP'] = []
        for i in range(h):
            v, _ = next(self)
            bmp.append(int(v, base=16) >> s)

    def _parse_kvp(self, ctx, k, v):
        if h := self.handlers.get(k):
            if (p := h(v)) is not None:
                ctx[k] = p
        elif v and v.isnumeric():
            ctx[k] = int(v)
        elif v:
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1].replace('""', '"')
            if v:
                if k in ctx:
                    ctx[k] = ctx[k] + '\n' + v
                else:
                    ctx[k] = v

    def _grok_font(self):
        font = Font()

        props = self.props
        font.copyright = props.get('COPYRIGHT', '')
        font.family = props.get('FAMILY_NAME', '')
        font.fullname = self.info['FONT']

        font.underline = [0, 1]
        font.caret = [0, 0]

        self._grok_metrics(font)
        self._grok_chars(font)
        self._grok_style(font)

        return font

    def _grok_metrics(self, font):
        bb = self.info['FONTBOUNDINGBOX']
        font.bbox = [ bb[2], bb[3], bb[0]+bb[2], bb[1]+bb[3] ]

        props = self.props
        asc = props.get('FONT_ASCENT', font.bbox[3])
        font.size = max(bb[0], bb[1])
        font.ascent = asc
        font.descent = props.get('FONT_DESCENT', -bb[3])
        font.capheight = props.get('CAP_HEIGHT', asc)
        font.xheight = props.get('X_HEIGHT', asc//2)
        font.linegap = 0 #max(0, font.bbox[3] - font.capheight)

    def _grok_style(self, font):
        props = self.props
        font.bold = props.get('WEIGHT_NAME', '').lower().startswith('bold')
        font.italic = props.get('SLANT', '').lower() in 'io'
        swn = props.get('SETWIDTH_NAME', '').lower()
        if not swn or not 'cond' in swn:
            font.condensed = None
        elif 'semi' in swn:
            font.condensed = 'SemiCondensed'
        else:
            font.condensed = 'Condensed'

        fixed = (font.glyphs[Glyph.NOTDEF].advance, 0)
        for glyph in font.glyphs.values():
            if glyph.advance not in fixed:
                font.fixedpitch = None
                break
        else:
            font.fixedpitch = int(ceil(fixed[0]))

    def _grok_chars(self, font):
        info = self.info
        gadv = info.get('SWIDTH', (None, None))
        size = info['SIZE']
        sx = size[0] * size[1] / 72
        sy = size[0] * size[2] / 72
        default = self.props.get('DEFAULT_CHAR', 0)
        glyphs = font.glyphs

        for ch in self.chars:
            code, name = ch['ENCODING'], ch['CHAR']
            if code == default:
                key, code, name = Glyph.NOTDEF, Glyph.NOTDEF, '.notdef'
            else:
                key = chr(code)
            assert key not in glyphs
            glyph = glyphs[key] = Glyph(code, name)

            bbx = ch['BBX']
            glyph.bbox = [ bbx[2], bbx[3], bbx[0]+bbx[2], bbx[1]+bbx[3] ]

            adv = ch.get('SWIDTH', gadv)
            assert adv[1] == 0
            glyph.advance = adv[0] * sx / 1000
            glyph.bitmap = ch['BITMAP']
