#!/usr/bin/env python3

import re
import sys
import json
import argparse
from pathlib import Path
from contextlib import nullcontext
from types import SimpleNamespace

def parse_args():
  parser = argparse.ArgumentParser(
    description="Insert kSEAL_DupSrc"
  )
  parser.add_argument("--dup-property-name", default="kSEAL_DupSrc",
    help="property name for duplicatd source info, default: kSEAL_DupSrc"
  )
  parser.add_argument("--seal-sources", default="SealSources.txt",
    help="SealSource.txt without duplicated source property, default: SealSources.txt"
  )
  parser.add_argument("--dup-tsv", default="-",
    help="filename of glyph name pairs for unencoded, and equivalent glyphs"
         "default: - (stdin)"
  )
  parser.add_argument("--verbose", "-v", action="count", default=0,
    help="verbose mode (multiple -v increases the level)"
  )
  parser.add_argument("--log", default=None,
    help="filename to log, default: None (stderr)"
  )
  args = parser.parse_args()

  if args.seal_sources == "-":
    args.ctx_seal_sources = nullcontext(sys.stdin)
  else:
    args.ctx_seal_sources = open(args.seal_sources, "r", encoding="utf-8")

  if args.dup_tsv == "-":
    args.ctx_dup_tsv = nullcontext(sys.stdin)
  else:
    args.ctx_dup_tsv = open(args.dup_tsv, "r", encoding="utf-8")

  if args.log is None:
    args.ctx_log = nullcontext(sys.stderr)
  else:
    args.ctx_log = open(args.log, "w+", encoding="utf-8")

  return args

def isMCJK(chr):
  ucs_cp = ord(chr)
  if 0x4E00 <= ucs_cp <= 0x9FFF:
    return "URO"
  elif 0x3400 <= ucs_cp <= 0x4DBF:
    return "ExtA"
  elif 0x20000 <= ucs_cp <= 0x2A6DF:
    return "ExtB"
  elif 0x2A700 <= ucs_cp <= 0x2B73F:
    return "ExtC"
  elif 0x2A740 <= ucs_cp <= 0x2B81F:
    return "ExtD"
  elif 0x2A820 <= ucs_cp <= 0x2CEAF:
    return "ExtE"
  elif 0x2CEB0 <= ucs_cp <= 0x2EBE0:
    return "ExtF"
  elif 0x30000 <= ucs_cp <= 0x3134F:
    return "ExtG"
  elif 0x31350 <= ucs_cp <= 0x323AF:
    return "ExtH"
  elif 0x2EBF0 <= ucs_cp <= 0x2EE5F:
    return "ExtI"
  elif 0x323B0 <= ucs_cp <= 0x3347F:
    return "ExtJ"
  elif 0xF900 <= ucs_cp <= 0xFAFF:
    return "CmptBMP"
  elif 0x2F800 <= ucs_cp <= 0x2FA1F:
    return "CmptSIP"
  else:
    return False


def mcjk_annotate(str):
  toks_out = []
  for chr in str:
    if isMCJK(chr):
      ucs_cp = ord(chr)
      toks_out.append(f"U+{ucs_cp:04X}:{chr}")
    else:
      toks_out.append(chr)
  return "".join(toks_out)


RE_UCS_HEX = re.compile(
  r"""
    (?P<uplus_hex>[Uu]\+[0-9A-Fa-f]+) |
    (?P<u_hex>u\+[0-9A-Fa-f]+)        |
    (?P<raw_hex>[0-9A-Fa-f]+)         |
    (?P<sep>[^0-9A-Fa-fUu\+])
  """,
  re.VERBOSE,
)


def mcjks_hex2utf8(mcjks):
  toks_out = []
  for m in RE_UCS_HEX.finditer(mcjks):
    kind = m.lastgroup
    tok = m.group()
    if kind == "uplus_hex":
      toks_out.append(f"U+{tok[2:]}:{chr(int(tok[2:], 16))}")
    elif kind == "u_hex":
      toks_out.append(f"U+{tok[1:]}:{chr(int(tok[1:], 16))}")
    elif kind == "raw_hex":
      toks_out.append(f"U+{tok}:{chr(int(tok, 16))}")
    else:
      toks_out.append(tok)
  return "".join(toks_out)


def update_set_seq(set_seq, prop_key, prop_value):
  if prop_key == "kSEAL_THXSrc":
    if prop_value.startswith("TH-Y"):
      set_seq["TH-Y"].add(int(prop_value.replace("TH-Y", "")))
    elif prop_value.startswith("TH-X"):
      set_seq["TH-X"].add(int(prop_value.replace("TH-X", "")))
    else:
      set_seq["TH-"].add(int(prop_value.replace("TH-", "")))
  elif prop_key == "kSEAL_CCZSrc":
    set_seq["C-"].add(int(prop_value.replace("C-", "")))
  elif prop_key == "kSEAL_QJZSrc":
    set_seq["K-"].add(int(prop_value.replace("K-", "")))
  elif prop_key == "kSEAL_DYCSrc":
    set_seq["D-"].add(int(prop_value.replace("D-", "")))


def parse_seal_sources(args, seal_source, glyph2ucs, set_seq):
  with args.ctx_seal_sources as fh:
    for line in fh:
      if not line.startswith("U+"):
        continue

      ucs_cp, prop_key, prop_value, = line.rstrip("\r\n").split("\t", 2)

      if ucs_cp not in seal_source:
        seal_source[ucs_cp] = {}
      seal_source[ucs_cp][prop_key] = prop_value

      if prop_key.startswith("kSEAL_") and prop_key.endswith("Src"):
        glyph2ucs[prop_value] = ucs_cp

      update_set_seq(set_seq, prop_key, prop_value)


def split_glyph_name(glyph_name):
  m = re.split(r"^(.*[^\d])(\d+)$", glyph_name)
  return [m[1], int(m[2]), len(m[2])]


class SealDB:
  def __init__(self, prefixes = []):
    self.sealSources = {}
    self.glyph2ucs = {}
    self.setSequences = {}
    self.missingGlyphs = {}
    self.ucs2dups = {}

    if len(prefixes) > 0:
      for prfx in prefixes:
        self.setSequences[prfx] = set()

  def getGlyphsAtUCS(self, ucs, prefix = None):
    glyphs = []
    dic = self.sealSources[ucs]
    for key, value in dic.items():
      if not key.startswith("kSEAL_"):
        continue
      if not key.endswith("Src"):
        continue

      _prefix, _seq, _len_seq, = split_glyph_name(value)
      if prefix is not None and prefix != _prefix:
        continue
      glyphs.append(value)

    return glyphs

  def getHorizontalGlyphs(self, glyph_name, dedup = False):
    if glyph_name not in self.glyph2ucs:
      return []
    ucs = self.glyph2ucs[glyph_name]

    glyphs = self.getGlyphsAtUCS(ucs)
    if dedup:
      glyphs = [
        g
        for g in glyphs
        if g != glyph_name
      ]
    return glyphs

  def getHorizontalGlyphForPrefix(self, glyph_name, prefix):
    for gn in self.getHorizontalGlyphs(glyph_name):
      _prfx, _seq, _len_seq, = split_glyph_name(gn)
      if prefix == _prfx:
        return gn
    return None


class MissingGlyph:
  def __init__(self, sealDB, glyph_name):
    self.glyphName = glyph_name
    prefix, seq, len_seq, = split_glyph_name(glyph_name)
    self.prefix = prefix
    self.seq = seq
    self.lenSeq = len_seq
    self.duplicated = None
    self.duplicatedUCS = None
    self.meta = SimpleNamespace()

    seq_gap_start = max([
      _seq
      for _seq in sealDB.setSequences[prefix]
      if _seq < self.seq
    ])
    self.gapStart = f"{prefix}{str(seq_gap_start).zfill(self.lenSeq)}"
    self.gapStartSeq = seq_gap_start
    self.gapStartUCS = sealDB.glyph2ucs[self.gapStart]
    self.gapOffset = self.seq - seq_gap_start

    seq_gap_end = min([
      _seq
      for _seq in sealDB.setSequences[prefix]
      if self.seq < _seq
    ])
    self.gapEnd = f"{prefix}{str(seq_gap_end).zfill(self.lenSeq)}"
    self.gapEndSeq = seq_gap_end
    self.gapEndUCS = sealDB.glyph2ucs[self.gapEnd]

  def __lt__(self, other):
    if type(other).__name__ == "str":
      return (self.glyphName < other)
    elif type(other).__name__ == type(self).__name__:
      return (self.glyphName < other.glyphName)
    else:
      raise ValueError("{type(self).__name__} cannot be compared with {type(other).__name__}")

  def __gt__(self, other):
    if type(other).__name__ == "str":
      return (self.glyphName > other)
    elif type(other).__name__ == type(self).__name__:
      return (self.glyphName > other.glyphName)
    else:
      raise ValueError("{type(self).__name__} cannot be compared with {type(other).__name__}")

  def __eq__(self, other):
    if type(other).__name__ == "str":
      return (self.glyphName == other)
    elif type(other).__name__ == type(self).__name__:
      return (self.glyphName == other.glyphName)
    else:
      raise ValueError("{type(self).__name__} cannot be compared with {type(other).__name__}")

  def corresponds(self, other):
    if type(self).__name__ != type(other).__name__:
      return False

    if self.gapStartUCS != other.gapStartUCS:
      return False

    if self.gapOffset != other.gapOffset:
      return False

    return True


def main():
  args = parse_args()

  sealDB = SealDB((
    "TH-", "TH-X", "TH-Y",
    "C-",
    "K-",
    "D-",
  ))

  with \
    args.ctx_dup_tsv as fh_dup, \
    args.ctx_log as fh_log:

    parse_seal_sources(args, sealDB.sealSources, sealDB.glyph2ucs, sealDB.setSequences)
    for prefix, seqs in sealDB.setSequences.items():
      max_seq = max(seqs)
      len_seq = len(str(max_seq))
      sealDB.missingGlyphs[prefix] = [
        MissingGlyph(sealDB, prefix + str(seq).zfill(len_seq))
        for seq in sorted(set(range(1, max(seqs) + 1)) - seqs)
      ]
      if args.verbose > 0:
        print(f"Unencoded {len(sealDB.missingGlyphs[prefix])} glyphs "
              f"for {prefix}: {', '.join([
                mg.glyphName for mg in sealDB.missingGlyphs[prefix]
              ])}",
              file=fh_log)


    for line in fh_dup:
      line = line.rstrip("\r\n")
      if len(line) == 0 or line.startswith("#"):
        continue

      toks = line.split("\t")
      if args.verbose > 2:
        print(toks, file=fh_log)
      glyph_unco = toks[0]
      glyph_enc  = toks[1]
      mcjks      = toks[2].split(",")
      prefixes   = toks[3].split(",")

      _mg = MissingGlyph(sealDB, glyph_unco)
      for _prfx in prefixes:
        mgs = [
          mg
          for mg in sealDB.missingGlyphs[_prfx]
          if _mg.corresponds(mg)
        ]
        if len(mgs) == 0:
          print(f"{glyph_unco} has no counter part in {_prfx}", file=fh_log)
          continue
        elif len(mgs) > 1:
          print(f"{glyph_unco} has multiple counter parts in {_prfx}", file=fh_log)
          continue
        mg = mgs[0]

        _ge = sealDB.getHorizontalGlyphForPrefix(glyph_enc, _prfx)
        mg.duplicated = _ge
        mg.duplicatedUCS = sealDB.glyph2ucs[_ge]
        mg.meta.comment_mcjks = mcjks

    for prefix, missingGlyphs in sealDB.missingGlyphs.items():
      for mg in missingGlyphs:
        if mg.duplicated is None:
          print("*** {mg.glyphName} is not resolved", fh_log)
          continue
        if mg.duplicatedUCS not in sealDB.ucs2dups:
          sealDB.ucs2dups[mg.duplicatedUCS] = {}
        if mg.glyphName not in sealDB.ucs2dups[mg.duplicatedUCS]:
          sealDB.ucs2dups[mg.duplicatedUCS][mg.glyphName] = mg

    # print(sealDB.ucs2dups)
    prefixes = [ "TH-", "C-", "K-", "D-" ]
    if args.verbose > 1:
      print(sealDB.ucs2dups.keys(), file=fh_log)
    for ucs_cp in sorted(sealDB.ucs2dups.keys()):
      dups = sorted(
        list(sealDB.ucs2dups[ucs_cp].keys()),
        key=lambda glyph_name: (
          prefixes.index(split_glyph_name(glyph_name)[0]),
          glyph_name
        )
      )

      mcjk_ss = sealDB.sealSources[ucs_cp]["kSEAL_MCJK"]
      mcjks_comment = ",".join(sealDB.ucs2dups[ucs_cp][dups[0]].meta.comment_mcjks)
      if args.verbose > 0:
        annotated_mcjk_ss = mcjks_hex2utf8(mcjk_ss)
        annotated_mcjks_comment = mcjk_annotate(mcjks_comment)
        print(f"\n# SEAL {ucs_cp} MCJK {annotated_mcjk_ss} (in {args.seal_sources}), "
              f"{annotated_mcjks_comment} (in {args.dup_tsv})")

      dups = " ".join(dups)
      print(f"{ucs_cp}\t{args.dup_property_name}\t{dups}")


if __name__ == "__main__":
  main()
