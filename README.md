# Omitted Glyph Names in SealSources.txt

Online demo is available at: [https://mpsuzuki.github.io/kSEAL_DUP/](https://mpsuzuki.github.io/kSEAL_DUP/).

## Duplicated Entries.

In some cases, the original _Shuowen Jiezi_ lists the exact same
character under multiple different radicals with identical analytical
descriptions and no graphical distinction (e.g., "𠮢" appearing in both
the "口" radical and the "又" radical).
To prevent duplicate encoding, the Unicode Standard encodes such
characters only once, omitting the redundant duplicate entries from the
repertoire.
Consequently, these deliberate omissions result in gaps (skips) in the
sequential source indexes within the code chart.

---

This is an attempt to propose an enhancement to SealSources.txt
documenting duplicated-and-unencoded source references in Seal.

Currently, SealSources.txt does not explicitly provide information on
which specific duplicated entries from the original Shuowen Jiezi (SWJZ)
sources were omitted from the Unicode code chart to prevent duplicate encoding.

While there is no need to modify the code chart itself, implementers
and researchers frequently need to track exactly which historical
source entries (e.g., from the THX, CCZ, QJZ, or DYC editions) were
identified as duplicates and consequently dropped from the repertoire.

Although the multi-valued kSEAL_Rad property serves as an initial indicator
that a given code point corresponds to multiple radicals in SWJZ,
it does not specify the precise structural locations or source indexes
of the omitted duplicate entries. Providing this missing
source-reference data -- either as an informative note in the text or
as a complementary data field -- would significantly enhance
the traceability and utility of the Seal dataset.

For example, current SealSources.txt gives some properties to U+3D3DD, like:
```
U+3D3DD	kSEAL_THXSrc	TH-00939
U+3D3DD	kSEAL_CCZSrc	C-00972
U+3D3DD	kSEAL_QJZSrc	K-00945
U+3D3DD	kSEAL_DYCSrc	D-00934
U+3D3DD	kSEAL_MCJK	20BA2
U+3D3DD	kSEAL_Rad	22.3D374 76.3D888
```

Here, the Small Seal character of "𠮢" (MCJK U+20BA2) is coded at U+3D3DD
(TH-00939, C-00972, K-00945, D-00934), the code position is located
under the radical "口."
As defined in SealSources.txt, the kSEAL_Rad property for U+3D3DD has
multiple space-separated values: "22.3D374" and "76.3D888".
The former "22.3D374" is for the 22nd radical corresponding to "口",
and "76.3D888" is for the 76th radical corresponding to "又".
It indicates that this character was duplicated in SWJZ.
But it is hard to identify which SWJZ entry was omitted.
In addition, some entries related with the duplicated glyphs do
not have the multiple values for kSEAL_Rad, for example, if the
duplicated glyphs are found in same radical, its kSEAL_Rad would
be single value property.

The proposed workaround for this issue is an addition of new
properties like:
```
U+3D3DD	kSEAL_AdditionalSrc	C-02157 D-02061 K-02083 TH-02078
```

The values means the glyph names of the omitted entries.
The users looking for a presentation glyph for these omitted glyphs,
they can use the glyph for U+3D3DD as a fallback glyph.
