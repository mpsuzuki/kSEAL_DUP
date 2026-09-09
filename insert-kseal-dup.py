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
  parser.add_argument("--log", default=None,
    help="filename to log, default: None (stderr)"
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


def get_prev_and_next_glyph(glyph_name, set_seq):
  prefix, seq, len_seq = split_glyph_name(glyph_name)

  if (seq - 1) not in set_seq[prefix]:
    raise ValueError(f"{seq - 1} not in {prefix}")

  if (seq + 1) not in set_seq[prefix]:
    raise ValueError(f"{seq + 1} not in {prefix}")

  return [
    f"{prefix}{str(seq - 1).zfill(len_seq)}",
    f"{prefix}{str(seq + 1).zfill(len_seq)}",
  ]


def main():
  args = parse_args()
  seal_source = {}

  glyph2ucs = {}
  set_seq = {
    "TH-": set(),
    "TH-X": set(),
    "TH-Y": set(),
    "C-": set(),
    "K-": set(),
    "D-": set(),
  }

  parse_seal_sources(args, seal_source, glyph2ucs, set_seq)

  ucs2dups = {}
  with args.ctx_dup_pairs as fh, args.ctx_log as fh_log:
    for line in fh:
      if line.startswith("#"):
        continue

      toks = line.rstrip("\r\n").split("\t")
      # print(toks)
      glyph_unco = toks[0]
      glyph_enc  = toks[1]
      dup_ucss   = toks[2]
      dup_ucs_hexs = ";".join([
        "U+" + hex(ord(u))[2:].upper() for u in dup_ucss.split(";")
      ])
      print([glyph_unco, glyph_enc, dup_ucss, dup_ucs_hexs])

      if not test_glyph_unco_enc(glyph_unco, glyph_enc, set_seq):
        continue

      ucs_cp = glyph2ucs[glyph_enc]
      mcjk = seal_source[ucs_cp]["kSEAL_MCJK"]
      mcjk_str = chr(int(mcjk, 16))

      if ucs_cp not in ucs2dups:
        ucs2dups[ucs_cp] = set()
      ucs2dups[ucs_cp].add(glyph_unco)

      glyph_prev, glyph_next, = get_prev_and_next_glyph(glyph_unco, set_seq)
      ucs_prev = glyph2ucs[glyph_prev]
      ucs_next = glyph2ucs[glyph_next]
      mcjk_prev = chr(int(seal_source[ucs_prev]["kSEAL_MCJK"], 16))
      mcjk_next = chr(int(seal_source[ucs_next]["kSEAL_MCJK"], 16))
      print(f"{glyph_prev}:{mcjk_prev} < {glyph_unco}:{mcjk_str} < {glyph_next}:{mcjk_next}")
      for src, prefix in [ ("THX", "TH-"),
                           ("CCZ", "C-"),
                           ("QJZ", "K-"),
                           ("DYC", "D-"), ]:
        prop_key = f"kSEAL_{src}Src"
        glyph_prev = seal_source[ucs_prev][prop_key]
        glyph_next = seal_source[ucs_next][prop_key]
        _prefix, seq_prev, _len_seq, = split_glyph_name(glyph_prev)
        _prefix, seq_next, _len_seq, = split_glyph_name(glyph_next)
        seq_avg = int((seq_prev + seq_next) / 2)
        glyph_avg = f"{_prefix}{str(seq_avg).zfill(_len_seq)}"
        if seq_avg in set_seq[_prefix]:
          print(f"{glyph_avg} corresponding to "
                f"U+{mcjk} {mcjk_str} is coded, do not include in kSEAL_DUP",
                file=fh_log
          )
        else:
          ucs2dups[ucs_cp].add(glyph_avg)

      glyphs_unco = ";".join(sorted(list(ucs2dups[ucs_cp])))
      print(f"{ucs_cp}\tkSEAL_DUP\t{glyphs_unco}\n")


if __name__ == "__main__":
  main()
