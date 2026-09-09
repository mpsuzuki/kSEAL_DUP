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
  parser.add_argument("--dup-multi", default="-",
    help="filename of glyph name pairs for unencoded, and equivalent glyphs for all versions"
         "default: - (stdin)"
  )
  parser.add_argument("--dup-single", default=None,
    help="filename of glyph name pairs for unencoded, and equivalent glyphs for single versions"
         "default: None"
  )
  parser.add_argument("--log", default=None,
    help="filename to log, default: None (stderr)"
  )
  args = parser.parse_args()

  if args.seal_sources == "-":
    args.ctx_seal_sources = nullcontext(sys.stdin)
  else:
    args.ctx_seal_sources = open(args.seal_sources, "r", encoding="utf-8")

  if args.dup_multi == "-":
    args.ctx_dup_multi = nullcontext(sys.stdin)
  else:
    args.ctx_dup_multi = open(args.dup_multi, "r", encoding="utf-8")

  if args.dup_single == "-":
    args.ctx_dup_single = nullcontext(sys.stdin)
  else:
    args.ctx_dup_single = open(args.dup_single, "r", encoding="utf-8")

  if args.log is None:
    args.ctx_log = nullcontext(sys.stderr)
  else:
    args.ctx_log = open(args.log, "w+", encoding="utf-8")

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
      prefix + str(seq).zfill(len_seq)
      for seq in sorted(set(range(1, max(seqs) + 1)) - seqs)
    ]
    print(f"Unencoded {len(sealDB.missingGlyphs[prefix])} glyphs "
          f"for {prefix}: {', '.join(sealDB.missingGlyphs[prefix])}")

  with \
    args.ctx_dup_single as fh_single, \
    args.ctx_dup_multi as fh_multi, \
    args.ctx_log as fh_log:

    set_glyph_unco_src_single = set()
    for line in fh_single:
      if not line.startswith("#"):
        proc_dup_line(line, sealDB, set_glyph_unco_src_single, False, fh_log)

    for prefix in sealDB.setSequences.keys():
      sealDB.missingGlyphs[prefix] = [
        g
        for g in sealDB.missingGlyphs[prefix]
        if g not in set_glyph_unco_src_single
      ]
      print(f"Unencoded {len(sealDB.missingGlyphs[prefix])} glyphs "
            f"for {prefix}: {', '.join(sealDB.missingGlyphs[prefix])}")

    set_glyph_unco_src_multi = set()
    for line in fh_multi:
      if not line.startswith("#"):
        proc_dup_line(line, sealDB, set_glyph_unco_src_multi, True, fh_log)


    prefixes = [ "TH", "C", "K", "D" ]
    for ucs_cp in sorted(sealDB.ucs2dups.keys()):
      dups = ";".join(sorted(
        list(sealDB.ucs2dups[ucs_cp]),
        key=lambda glyph_name: (
          prefixes.index(glyph_name.split("-")[0]),
          glyph_name
        )
      ))
      print(f"{ucs_cp}\tkSEAL_DUP\t{dups}")


if __name__ == "__main__":
  main()
