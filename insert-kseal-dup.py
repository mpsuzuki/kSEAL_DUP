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
  parser.add_argument("--dup-pairs", default="-",
    help="filename of glyph name pairs for duplicated & unencoded glyph, and equivalent glyph, "
         "default: - (stdin)"
  )
  args = parser.parse_args()

  if args.seal_sources == "-":
    args.ctx_seal_sources = nullcontext(sys.stdin)
  else:
    args.ctx_seal_sources = open(args.seal_sources, "r", encoding="utf-8")

  if args.dup_pairs == "-":
    args.ctx_dup_pairs = nullcontext(sys.stdin)
  else:
    args.ctx_dup_pairs = open(args.dup_pairs, "r", encoding="utf-8")

  return args

def main():
  args = parse_args()
  seal_source = {}

  glyph2ucs = {}
  ucs2dups = {}
  set_th = set()
  set_th_x = set()
  set_th_y = set()
  set_ccz = set()
  set_qjz = set()
  set_dyc = set()
  
  with args.ctx_seal_sources as fh_ss:
    for line in fh_ss:
      if not line.startswith("U+"):
        continue

      toks = line.rstrip("\r\n").split("\t", 2)
      # print(toks)
      ucs_cp = toks[0]
      prop_key = toks[1]
      prop_value = toks[2]

      if ucs_cp not in seal_source:
        seal_source[ucs_cp] = {}
      seal_source[ucs_cp][prop_key] = prop_value

      if prop_key.startswith("kSEAL_") and prop_key.endswith("Src"):
        glyph2ucs[prop_value] = ucs_cp

      if prop_key == "kSEAL_THXSrc":
        if prop_value.startswith("TH-Y"):
          set_th_y.add(int(prop_value.replace("TH-Y", "")))
        elif prop_value.startswith("TH-X"):
          set_th_x.add(int(prop_value.replace("TH-X", "")))
        else:
          set_th.add(int(prop_value.replace("TH-", "")))
      elif prop_key == "kSEAL_CCZSrc":
        set_ccz.add(int(prop_value.replace("C-", "")))
      elif prop_key == "kSEAL_QJZSrc":
        set_qjz.add(int(prop_value.replace("K-", "")))

  with args.ctx_dup_pairs as fh_dp:
    for line in fh_dp:
      if line.startswith("#"):
        continue

      toks = line.rstrip("\r\n").split("\t")
      print(toks)
      glyph_unencoded = toks[0]
      glyph_encoded = toks[1]

      seq_unencoded = glyph_unencoded.split("-",1).pop()
      seq_encoded = glyph_encoded.split("-",1).pop()

      if re.match(r"^\d+$", seq_unencoded) is None:
        continue

      if re.match(r"^\d+$", seq_encoded) is None:
        continue

      seq_unencoded = int(seq_unencoded)
      seq_encoded = int(seq_encoded)
      print([seq_unencoded, seq_encoded])

      if glyph_unencoded.startswith("C-"):
        if seq_unencoded in set_ccz:
          continue
        if seq_encoded not in set_ccz:
          continue

        ucs_cp = glyph2ucs[glyph_encoded]
        if ucs_cp not in ucs2dups:
          ucs2dups[ucs_cp] = set()
        ucs2dups[ucs_cp].add(glyph_unencoded)
        print(f"{ucs_cp}\tkSEAL_DUP\t{glyph_unencoded}")

if __name__ == "__main__":
  main()
