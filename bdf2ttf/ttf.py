from math import log2, ceil, pi, tan
from array import array
from collections import namedtuple
from struct import pack, unpack
from datetime import datetime, timezone
import re


class TTFWriter:
    def __init__(self, font):
        self.font = font

        glyphs = self.glyphs = sorted(
            (g for c, g in font.glyphs.items()
             if g.code == c or g.code == ord(c)),
            key=lambda g: g.code
        )

        # NB offsets are determined by writing glyf, which is *after* loca
        offsets = array('I', (0 for _ in range(len(glyphs)+1)))

        # init tables w/defaults that can be overridden
        self.head = Header(font)
        self.hhea = HorizontalHeader(font, glyphs)
        self.maxp = MaximumProfile(font, glyphs)
        self.os2 = OS2(font)
        self.hmtx = HorizontalMetrics(font, glyphs)
        self.cmap = CharacterMap(font, glyphs)
        self.loca = LocationIndex(font, offsets)
        self.glyf = GlyphData(font, glyphs, offsets)
        self.name = Naming(font)
        self.post = PostScript(font)
        self.gasp = Grayscale(font)

        # recommended table order from OpenType spec
        self.tables = [
            self.head, self.hhea, self.maxp, self.os2,
            self.hmtx, # 'LTSH' 'VDMX' 'hdmx'
            self.cmap, # 'fpgm' 'prep' 'cvt '
            self.loca, self.glyf, # 'kern'
            self.name, self.post, self.gasp, # 'PCLT', 'DSIG'
        ]

    TTF_SCALER = 0x00010000

    def write(self, file):
        start = file.tell()
        tabs = self.tables
        ntabs = len(tabs)
        splitl2 = int(log2(ntabs|1))
        split = 1 << splitl2
        rem = max(0, ntabs - split)
        wrpk(file, '>I4H',
            self.TTF_SCALER, ntabs, split*0x10, splitl2, rem*0x10)

        tocoff = file.tell()
        file.write(bytes(ntabs * 0x10))  # reserve space for ToC

        for tab in tabs:
            self.write_table(file, tab)
        end = file.tell()

        # overwrite loca reservation w/updated offsets
        assert self.loca.offsets[-1]
        file.seek(self.loca.offset)
        self.write_table(file, self.loca)

        file.seek(tocoff)
        for tab in sorted(tabs, key=lambda t: t.tag):
            wrpk(file, '>4s3I',
                tab.tag.ljust(4).encode(), tab.chksum, tab.offset, tab.size)

        file.seek(start)
        self.head.update_checksum(file, sum_file_u32(file, end-start))

    @staticmethod
    def write_table(file, table):
        table.offset = file.tell()
        table.write(file)
        end = file.tell()

        table.size = end - table.offset
        file.write(bytes(4-(end&3) & 3))
        assert not file.tell()&3

        file.seek(table.offset)
        table.chksum = sum_file_u32(file, table.size)


class Table:
    def __init__(self, font, glyphs=None):
        self.font = font
        self.glyphs = glyphs


class Header(Table):
    tag = 'head'
    TTF_VERSION = 1.0
    TTF_MAGIC = 0x5f0f3cf5
    CHK_MAGIC = 0xb1b0afba

    def __init__(self, font):
        super().__init__(font)
        self.flags = 0b1011
        self.indexfmt = 1

        now = datetime.now(timezone.utc)
        epoch = datetime(1904, 1, 1, tzinfo=timezone.utc)
        self.created = self.modified = int((now - epoch).total_seconds())

        style = 0
        if font.bold: style |= 1<<0
        if font.italic: style |= 1<<1
        if font.condensed: style |= 1<<5
        self.style = style

        self.lowestRecPPEM = 6  # arbitrary default

    def write(self, file):
        font = self.font
        print(f'head: flags={self.flags:02x} em={int(round(font.size))}'
              f' bbox={font.bbox} style={self.style:02x}')

        wrpk(file, '>II4xI HHQQ 4hHH 3h',
            p16(self.TTF_VERSION), p16(font.version), self.TTF_MAGIC,
            self.flags, round(font.size), self.created, self.modified,
            *font.bbox, self.style, self.lowestRecPPEM,
            2, self.indexfmt, 0)

    def update_checksum(self, file, chk):
        file.seek(self.offset + 8)
        wrpk(file, '>I', (self.CHK_MAGIC - chk) & (1<<32)-1)


NameRec = namedtuple('NameRec', 'plat enc lang id str')


class Naming(Table):
    tag = 'name'

    def __init__(self, font):
        super().__init__(font)
        names = self.names = []

        styles = []
        if font.bold: styles.append('Bold')
        if font.italic: styles.append('Italic')
        #if font.condensed: styles.append(font.condensed)
        if not styles:
            styles.append('Regular')

        # "Name ID 1 to 6 are often needed to be installable"
        assert font.family, 'family name is required'
        longname = ' '.join([font.family] + styles)
        psfamily = re.sub(r'[^0-9A-Za-z]', '', font.family)
        self.psname = f'{psfamily}-{"".join(styles)}'
        fullname = font.fullname or psname
        names.append(NameRec(0, 3, 0, 0, font.copyright or ''))
        names.append(NameRec(0, 3, 0, 1, font.family))
        names.append(NameRec(0, 3, 0, 2, ' '.join(styles)))
        names.append(NameRec(0, 3, 0, 3, fullname))
        names.append(NameRec(0, 3, 0, 4, longname))
        names.append(NameRec(0, 3, 0, 5, f'Version {font.version}'))

        # OpenType fonts that include a name with name ID of 6 should include
        # these two names with name ID 6, and characteristics as follows:
        # Platform: 1 [Macintosh]; Platform-specific encoding: 0 [Roman]; Language: 0 [English].
        # Platform: 3 [Windows]; Platform-specific encoding: 1 [Unicode]; Language: 0x409 [English (American)].

        # ftxvalidator complains if psname is 0/3
        #names.append(NameRec(0, 3, 0, 6, self.psname))
        names.append(NameRec(1, 0, 0, 6, self.psname))
        names.append(NameRec(3, 1, 0x409, 6, self.psname))

    def write(self, file):
        names = self.names
        n = len(names)
        wrpk(file, '>3H', 0, n, 6+12*n)
        off = 0
        data = []
        for nm in names:
            match (nm.plat, nm.enc):
                case (0, _) | (3, 1):
                    enc = 'utf-16be'
                case (1, 0):
                    enc = 'macroman'
                case _:
                    assert None

            d = nm.str.encode(enc)
            nb = len(d)
            print(f'[{nm.id:02x}] ({nm.plat:02x}/{nm.enc:02x}/{nm.lang:02x})'
                  f' {off:04x}+{nb:04x} \"{nm.str}\"')
            wrpk(file, '>6H', nm.plat, nm.enc, nm.lang, nm.id, nb, off)
            data.append(d)
            off += nb
        for d in data:
            file.write(d)


class PostScript(Table):
    tag = 'post'

    def __init__(self, font):
        super().__init__(font)
        self.format = 3

    def write(self, file):
        font = self.font
        wrpk(file, '>IihhI16x',
            p16(self.format), p16(font.caret[0]), *font.underline,
            1 if font.fixedpitch else 0)
        assert self.format in (1, 3), 'FIXME subtable'


class MaximumProfile(Table):
    tag = 'maxp'

    def __init__(self, *args):
        super().__init__(*args)
        self.version = 1.0

    def write(self, file):
        wrpk(file, '>I', p16(self.version))
        assert self.version == 1.0
        self._write_v1(file)

    def _write_v1(self, file):
        maxpts, maxctrs = 0, 0
        for g in self.glyphs:
            ctrs = g.contours
            nc = len(ctrs)
            np = sum(len(c) for c in ctrs)
            if maxpts < np: maxpts = np
            if maxctrs < nc: maxctrs = nc

        wrpk(file, '>6H16x', len(self.glyphs), maxpts, maxctrs, 0, 0, 2)


class OS2(Table):
    tag = 'OS/2'

    def __init__(self, font):
        super().__init__(font)
        self.version = 5
        self.weight = 700 if font.bold else 500

        if not font.condensed:
            self.width = 5
        elif 'semi' in font.condensed:
            self.width = 4
        else:
            self.width = 3

        codes = [ ord(c) if isinstance(c, str) else c for c in font.glyphs ]
        self.mincode = min(c for c in codes if c >= 0)
        self.maxcode = max(codes)

        self.strikeout = font.underline.copy()
        self.strikeout[0] += font.xheight - self.strikeout[1]

        fssel = 0
        if font.italic: fssel |= 1<<0
        if font.bold: fssel |= 1<<5
        if not fssel: fssel |= 1<<6
        self.fsSelection = fssel

        # FIXME apply caret
        bb = font.bbox
        x1, ymid = bb[2]//2, (bb[1]+bb[3])//2
        self.subscript = [ 0, -bb[1]//2, x1, ymid ]
        self.superscript = [ 0, ymid - bb[1]//2, x1, bb[3] ]

        panose = self.panose = bytearray(10)
        # Windows uses bFamilyType, bSerifStyle and bProportion
        panose[0] = 2  # just assume "Latin Text"
        panose[1] = 11  # and "Normal Sans Serif"
        # panose.bProportion must be set to 9 [for monospace] latin text fonts
        if font.fixedpitch:
            panose[3] = 9

    def write(self, file):
        font = self.font
        mask32 = (1<<32) - 1

        sub, sup = self.subscript, self.superscript
        wrpk(file, '>Hh 3H 11h 10B 4I 4s3H 3hHH Q hh3H 2H',
            self.version, font.fixedpitch,
            self.weight, self.width, 0,
            sub[2]-sub[0], sub[3]-sub[1], sub[0], sub[1],
            sup[2]-sup[0], sup[3]-sup[1], sup[0], sup[1],
            self.strikeout[1], self.strikeout[0], 0,
            *self.panose,
            0, 0, 0, 0,  # only for cmap 3/*
            b'    ', self.fsSelection, self.mincode,
            min(self.maxcode, (1<<16)-1),
            font.ascent, -font.descent, font.linegap,
            font.ascent, font.descent,
            0,  # only for cmap 3/*
            font.xheight, font.capheight,
            0, 0x20, 0, # FIXME maxContext=1?
            0, 0xffff)


class Grayscale(Table):
    tag = 'gasp'

    def __init__(self, font):
        super().__init__(font)
        self.version = 0
        self.ranges = [
            (0xffff, 0x0001)
        ]

    def write(self, file):
        wrpk(file, '>HH', self.version, len(self.ranges))
        for r in self.ranges:
            wrpk(file, '>HH', *r)


class HorizontalHeader(Table):
    tag = 'hhea'

    def __init__(self, *args):
        super().__init__(*args)
        self.version = 1.0
        size, caret = self.font.size, self.font.caret
        self.caret = [
            size,
            round(size * tan(-pi/180 * caret[0])),
            caret[1]
        ]

    def write(self, file):
        font = self.font
        maxadv = 0
        maxext = 0
        minlsb = 9999
        minrsb = 9999
        for g in self.glyphs:
            lsb, _, ext, _ = g.calc_bbox()
            adv = g.advance
            rsb = adv - ext
            if maxadv < adv: maxadv = adv
            if maxext < ext: maxext = ext
            if minlsb > lsb: minlsb = lsb
            if minrsb > rsb: minrsb = rsb

        #assert font.caret[0] == 0

        print(f'hhea: ascent={font.ascent} descent={font.descent}'
              f' linegap={font.linegap} fixed={font.fixedpitch}')
        print(f'\tmaxadv={maxadv} maxext={maxext}'
              f' minlsb={minlsb} minrsb={minrsb}')

        wrpk(file, '>I3h H6h10xh', p16(self.version),
            font.ascent, -font.descent, font.linegap,
            maxadv, minlsb, minrsb, maxext, *self.caret,
            # "It is suggested that monospaced fonts set numberOfHMetrics to 3"
            len(self.glyphs))


class HorizontalMetrics(Table):
    tag = 'hmtx'

    def write(self, file):
        font = self.font
        # FIXME implement that tail compression
        for g in self.glyphs:
            wrpk(file, '>Hh', g.advance, g.calc_bbox()[0])


class CharacterMap(Table):
    tag = 'cmap'

    def __init__(self, font, glyphs):
        super().__init__(font, glyphs)

        index = { g: i for i, g in enumerate(glyphs) }
        cmap = {
            ord(c) if isinstance(c, str) else c: index[g]
            for c, g in font.glyphs.items()
        }
        maxcode = max(cmap.keys())
        assert maxcode == glyphs[-1].code
        segs = self.segs = self.segment(cmap)
        print(f'cmap: {len(cmap)} codepoints maxcode={maxcode:04x}'
              f' {len(segs)} segments')

        subtabs = self.subtabs = [ CMAPSegmentDelta(segs) ]
        if maxcode >= 1<<16:
            subtabs.append(CMAPSegmentCoverage(segs))

    @staticmethod
    def segment(cmap):
        seg = [ None, None, None ]
        segs = []
        for code in sorted(cmap.keys()):
            if code < 0: continue
            idx = cmap[code]
            if code-1 == seg[-1] and idx-1 == seg[0] + seg[2]-seg[1]:
                seg[-1] = code
            else:
                seg = [ idx, code, code ]
                segs.append(seg)
        return segs

    def write(self, file):
        subtabs = self.subtabs
        subtabs.sort(key=lambda tab: (tab.platform, tab.encoding))

        start = file.tell()
        wrpk(file, '>2H', 0, len(subtabs))

        off = 2*2 + 8*len(subtabs)
        for tab in subtabs:
            wrpk(file, '>2HI', tab.platform, tab.encoding, off)
            off += tab.size

        for tab in subtabs:
            tab.offset = file.tell()
            tab.write(file)
            assert file.tell() - tab.offset == tab.size


class CMAPSegmentDelta:
    platform = 0
    encoding = 3

    def __init__(self, segs):
        segs = self.segs = segs[:]
        while segs[-1][1] > 0xffff:
            segs.pop()
        if segs[-1][-1] > 0xffff:
            segs[-1] = segs[-1][:2] + [ 0xffff ]
        if segs[-1][-1] < 0xffff:
            segs.append([ 0, 0xffff, 0xffff ])

    @property
    def size(self):
        return 2*8 + 2*4*len(self.segs)

    def write(self, file):
        segs = self.segs
        nsegs = len(segs)
        splitl2 = int(log2(nsegs|1))
        split = 1 << splitl2
        rem = max(0, nsegs - split)

        off0 = file.tell()
        wrpk(file, '>7H', 4, self.size, 0, nsegs*2, split*2, splitl2, rem*2)

        for seg in segs:
            wrpk(file, '>H', seg[-1])
        wrpk(file, '>2x')
        for seg in segs:
            wrpk(file, '>H', seg[1])
        for seg in segs:
            delta = seg[0]-seg[1] & 0xffff
            wrpk(file, '>H', delta)
        file.write(b'\0' * (2*nsegs))


class CMAPSegmentCoverage:
    platform = 0
    encoding = 4

    def __init__(self, segs):
        self.segs = segs

    @property
    def size(self):
        return 4*(4 + 3*len(self.segs))

    def write(self, file):
        segs = self.segs
        wrpk(file, '>2H3I', 12, 0, self.size, 0, len(segs))
        for glyph0, char0, char1 in segs:
            wrpk(file, '>3I', char0, char1, glyph0)


class GlyphData(Table):
    tag = 'glyf'

    def __init__(self, font, glyphs, offsets):
        super().__init__(font, glyphs)
        self.offsets = offsets

    def write(self, file):
        font = self.font
        off0 = file.tell()

        for i, g in enumerate(self.glyphs):
            self.offsets[i] = file.tell() - off0 # save for loca index
            self._write_glyph(file, g)

            # Font-Validator W1701 "Loca references a glyf entry which length is not a multiple of 4"
            file.write(bytes(4-(file.tell()&3) & 3))

        self.offsets[i+1] = file.tell() - off0 # save for loca index

    def _write_glyph(self, file, glyph):
        ctrs = glyph.contours
        nctrs = len(ctrs)
        if nctrs == 0:
            return # no data written

        wrpk(file, '>5h', nctrs, *glyph.calc_bbox())

        n = 0
        for c in ctrs:
            assert c
            n += len(c)
            wrpk(file, '>H', n-1)

        wrpk(file, '>H', 0)  # no hinting...

        xs = [ p[0] for c in ctrs for p in c ]
        ys = [ p[1] for c in ctrs for p in c ]
        for i in reversed(range(1, n)):  # convert to relative
            xs[i] -= xs[i-1]
            ys[i] -= ys[i-1]

        def classify_coord(du):
            if du == 0:
                return 1<<4
            if abs(du) >= 0x100:
                return 0
            if du > 0:
                return 1<<1 | 1<<4
            return 1<<1

        flags = bytes(
            1 | classify_coord(dx) | classify_coord(dy)<<1
            for dx, dy in zip(xs, ys)
        )

        for i in reversed(range(n)):
            if flags[i] & 0x12 == 0x10:
                del xs[i]
            if flags[i]>>1 & 0x12 == 0x10:
                del ys[i]

        # FIXME RLE compress flags
        file.write(flags)

        for u in xs:
            if abs(u) >= 0x100:
                wrpk(file, '>h', u)
            else:
                wrpk(file, '>B', abs(u))

        for u in ys:
            if abs(u) >= 0x100:
                wrpk(file, '>h', u)
            else:
                wrpk(file, '>B', abs(u))

        if file.tell() & 1:
            wrpk(file, '>x')


class LocationIndex(Table):
    tag = 'loca'

    def __init__(self, font, offsets):
        super().__init__(font)
        self.offsets = offsets

    def write(self, file):
        for off in self.offsets:
            wrpk(file, '>I', off)


def p16(v):
    return int(v * (1<<16))


def wrpk(file, fmt, *args):
    try:
        file.write(pack(fmt, *args))
    except:
        print(fmt, args)
        raise


def sum_file_u32(file, size):
    return sum(
        unpack('>I', file.read(4))[0]
        for j in range((size + 3) // 4)
    ) & (1<<32)-1
