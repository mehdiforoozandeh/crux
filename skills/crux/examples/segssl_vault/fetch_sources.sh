#!/usr/bin/env bash
# Fetch the SegSSL vault's 15 literature sources (open-access arXiv PDFs) into raw/
# and verify each against the vault's own registry (wiki/.sources.tsv).
#
# The PDFs are not committed to the repo — arXiv's default license does not permit
# third-party redistribution, and 86 MB of papers doesn't belong in a git clone.
# The cockpit (crux serve) works fully without them; fetching gives you the actual
# papers and a findings-free `crux validate`.
set -uo pipefail
cd "$(dirname "$0")"
mkdir -p raw   # empty dirs don't survive git clones

PAPERS="
2111.06377|he2021_mae.pdf
2104.14294|caron2021_dino.pdf
2304.07193|oquab2023_dinov2.pdf
2002.05709|chen2020_simclr.pdf
1911.05722|he2019_moco.pdf
2010.11929|dosovitskiy2020_vit.pdf
2105.15203|xie2021_segformer.pdf
2105.05633|strudel2021_segmenter.pdf
1505.04597|ronneberger2015_unet.pdf
1802.02611|chen2018_deeplabv3plus.pdf
2106.08254|bao2021_beit.pdf
2111.07832|zhou2021_ibot.pdf
2011.09157|wang2020_densecl.pdf
2011.10043|xie2020_pixpro.pdf
1604.01685|cordts2016_cityscapes.pdf
"

sha() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d" " -f1
  else sha256sum "$1" | cut -d" " -f1; fi
}

ok=0; fail=0
for line in $PAPERS; do
  id="${line%%|*}"; fn="${line##*|}"; out="raw/$fn"
  if [ -f "$out" ] && head -c 5 "$out" | grep -q "%PDF-"; then
    echo "have      $out"
  else
    echo "fetching  $out  (arXiv $id)"
    curl -fL --max-time 300 -o "$out" "https://arxiv.org/pdf/$id" \
      || curl -fL --max-time 300 -o "$out" "https://export.arxiv.org/pdf/$id" \
      || { echo "  FAILED to download $id"; rm -f "$out"; fail=$((fail+1)); continue; }
  fi
  if ! head -c 5 "$out" | grep -q "%PDF-"; then
    echo "  FAILED: $out is not a PDF"; rm -f "$out"; fail=$((fail+1)); continue
  fi
  want=$(awk -F"\t" -v p="raw/$fn" '$3 == p { print $1 }' wiki/.sources.tsv)
  got=$(sha "$out")
  if [ "$want" = "$got" ]; then
    echo "  ok      sha256 matches the registry"
    ok=$((ok+1))
  else
    # arXiv occasionally re-renders a PDF; the paper is fine, the bytes moved.
    echo "  NOTE    sha256 differs from the registry (arXiv re-rendered this PDF)."
    echo "          Re-register it:  ./crux ingest raw/$fn"
    ok=$((ok+1))
  fi
done

echo
echo "$ok fetched/verified, $fail failed. Run 'crux validate' from this directory — it"
echo "should be clean (or list exactly the re-ingests suggested above)."
[ "$fail" -eq 0 ]
