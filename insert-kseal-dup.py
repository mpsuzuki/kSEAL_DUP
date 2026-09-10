#!/usr/bin/env python3

import re
import sys
import json
import argparse
from pathlib import Path
from contextlib import nullcontext

def parse_args():
  parser = argparse.ArgumentParser(
    description="Insert kSEAL_DUP"
  )
  parser.add_argument("--seal-sources", default="SealSources.txt",
    help="SealSource.txt without kSEAL_DUP property, default: SealSources.txt"
  )
  parser.add_argument("--dup-merged", default="-",
    help="filename of glyph name pairs for unencoded, and equivalent glyphs"
         "default: - (stdin)"
  )
  parser.add_argument("--log", default=None,
    help="filename to log, default: None (stderr)"
  )
  parser.add_argument("--prefixes-universal", default="TH-,C-,K-,D-",
    help="glyph prefixes for universal duplications, "
         "default: TH-,C-,K-,D-"
  )
  args = parser.parse_args()

  if args.seal_sources == "-":
    args.ctx_seal_sources = nullcontext(sys.stdin)
  else:
    args.ctx_seal_sources = open(args.seal_sources, "r", encoding="utf-8")

  if args.dup_merged == "-":
    args.ctx_dup_merged = nullcontext(sys.stdin)
  else:
    args.ctx_dup_merged = open(args.dup_merged, "r", encoding="utf-8")

  if args.log is None:
    args.ctx_log = nullcontext(sys.stderr)
  else:
    args.ctx_log = open(args.log, "w+", encoding="utf-8")

  args.prefixes_universal = args.prefixes_universal.split(",")
  args.set_prefixes_universal = set(args.prefixes_universal)

  return args

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


def validate_glyph_name(glyph_name, test_prefix = False):
  prefix, seq, len_seq, = split_glyph_name(glyph_name)

  if len(prefix) == 0 or len_seq == 0:
    return False

  if test_prefix and prefix not in ("TH-", "TH-X", "TH-Y", "C-", "K-", "D-"):
    return False

  return True


def test_glyph_unco_enc(glyph_unco, glyph_enc, set_seq):
  prefix_unco, seq_unco, len_seq_unco, = split_glyph_name(glyph_unco)
  prefix_enc,  seq_enc,  len_seq_enc,  = split_glyph_name(glyph_enc)

  if prefix_unco != prefix_enc:
    return False

  if len_seq_unco != len_seq_enc:
    return False

  if prefix_unco not in set_seq:
    return False

  if prefix_enc not in set_seq:
    return False

  if seq_unco in set_seq[prefix_unco]:
    return False

  if seq_enc not in set_seq[prefix_enc]:
    return False

  return True

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
    # print(dic)
    for key, value in dic.items():
      if not key.startswith("kSEAL_"):
        continue
      if not key.endswith("Src"):
        continue

      # print(key, value)
      _prefix, _seq, _len_seq, = split_glyph_name(value)
      if prefix is not None and prefix != _prefix:
        continue
      glyphs.append(value)

    return glyphs

  def getHorizontalGlyphs(self, glyph_name, dedup = False):
    # print(glyph_name)
    if glyph_name not in self.glyph2ucs:
      return []
    ucs = self.glyph2ucs[glyph_name]

    # print(ucs)
    glyphs = self.getGlyphsAtUCS(ucs)
    # print(glyphs)
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

def proc_dup_line(line, sealDB, set_glyph_unco, multi_source = False, log=sys.stderr):
  toks = line.rstrip("\r\n").split("\t")
  glyph_unco = toks[0]
  glyph_enc  = toks[1]
  dup_ucss   = toks[2]
  dup_ucs_hexs = ";".join([
    "U+" + hex(ord(u))[2:].upper() for u in dup_ucss.split(";")
  ])
  print([glyph_unco, glyph_enc, dup_ucss, dup_ucs_hexs])

  if not test_glyph_unco_enc(glyph_unco, glyph_enc, sealDB.setSequences):
    return

  if set_glyph_unco is not None:
    set_glyph_unco.add(glyph_unco)

  ucs_cp = sealDB.glyph2ucs[glyph_enc]
  if ucs_cp is None:
    print(f"{glyph_enc} is not coded", file=logt_fh)
  if ucs_cp not in sealDB.ucs2dups:
    sealDB.ucs2dups[ucs_cp] = set()
  sealDB.ucs2dups[ucs_cp].add(glyph_unco)

  if not multi_source:
    return

  prefix, seq, len_seq, = split_glyph_name(glyph_unco)
  try:
    index_unco = sealDB.missingGlyphs[prefix].index(glyph_unco)
    for _prfx in sealDB.missingGlyphs.keys():
      if prefix == _prfx:
        continue
      if index_unco < len(sealDB.missingGlyphs[_prfx]):
        _g_unco = sealDB.missingGlyphs[_prfx][index_unco]
        print(f"\t{glyph_unco} -> {_g_unco}")

        set_glyph_unco.add(glyph_unco)
        sealDB.ucs2dups[ucs_cp].add(_g_unco)

  except:
    print(f"{glyph_unco} is not found ", file=log)




def main():
  args = parse_args()

  sealDB = SealDB((
    "TH-", "TH-X", "TH-Y",
    "C-",
    "K-",
    "D-",
  ))

  parse_seal_sources(args, sealDB.sealSources, sealDB.glyph2ucs, sealDB.setSequences)
  for prefix, seqs in sealDB.setSequences.items():
    max_seq = max(seqs)
    len_seq = len(str(max_seq))
    sealDB.missingGlyphs[prefix] = [
      MissingGlyph(sealDB, prefix + str(seq).zfill(len_seq))
      for seq in sorted(set(range(1, max(seqs) + 1)) - seqs)
    ]
    print(f"Unencoded {len(sealDB.missingGlyphs[prefix])} glyphs "
          f"for {prefix}: {', '.join([
            mg.glyphName for mg in sealDB.missingGlyphs[prefix]
          ])}")

  with \
    args.ctx_dup_merged as fh_merged, \
    args.ctx_log as fh_log:


    for line in fh_merged:
      line = line.rstrip("\r\n")
      if len(line) == 0 or line.startswith("#"):
        continue

      toks = line.split("\t")
      print(toks)
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

    for prefix, missingGlyphs in sealDB.missingGlyphs.items():
      for mg in missingGlyphs:
        if mg.duplicatedUCS not in sealDB.ucs2dups:
          sealDB.ucs2dups[mg.duplicatedUCS] = set()
        sealDB.ucs2dups[mg.duplicatedUCS].add(mg.glyphName)

    prefixes = [ "TH", "C", "K", "D" ]
    print(sealDB.ucs2dups.keys())
    for ucs_cp in sorted(sealDB.ucs2dups.keys()):
      dups = " ".join(sorted(
        list(sealDB.ucs2dups[ucs_cp]),
        key=lambda glyph_name: (
          prefixes.index(glyph_name.split("-")[0]),
          glyph_name
        )
      ))
      print(f"{ucs_cp}\tkSEAL_DUP\t{dups}")


if __name__ == "__main__":
  main()
