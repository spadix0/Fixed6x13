from argparse import ArgumentParser, FileType
from importlib import util as importer
from pathlib import Path

from .convert import bdf2ttf


parser = ArgumentParser('bdf2ttf',
    description='convert BDF bitmap font into simple TrueType outlines')
parser.add_argument('--mod', type=Path, metavar='MOD.py',
    help='python code to apply changes to font after loading')
parser.add_argument('bdf', type=FileType(), metavar='font.bdf',
    help='BDF font file to convert')

args = parser.parse_args()

if modpath := args.mod:
    modname = modpath.stem.replace('.', '_')
    spec = importer.spec_from_file_location(modname, modpath)
    mod = importer.module_from_spec(spec)
    spec.loader.exec_module(mod)
else:
    mod = None

bdf2ttf(args.bdf, mod)
