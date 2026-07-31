#!/usr/bin/env bash
# Fetch this vault's 22 literature sources (open-access arXiv PDFs) into raw/
# and verify each against the vault's own registry (wiki/.sources.tsv).
#
# The PDFs are not committed to the repo — arXiv's default license does not permit
# third-party redistribution, and ~80 MB of papers doesn't belong in a git clone.
# The cockpit (crux serve) works fully without them; fetching gives you the actual
# papers and a findings-free `crux validate`.
set -uo pipefail
cd "$(dirname "$0")"
mkdir -p raw   # empty dirs don't survive git clones

PAPERS="
2001.08361|kaplan2020_scaling_laws.pdf
2203.15556|hoffmann2022_chinchilla.pdf
1712.00409|hestness2017_scaling_predictable.pdf
1707.02968|sun2017_revisiting_data.pdf
1909.12673|rosenfeld2019_error_across_scales.pdf
2106.04560|zhai2021_scaling_vit.pdf
2102.06701|bahri2021_explaining_scaling.pdf
2206.14486|sorscher2022_data_pruning.pdf
2010.11929|dosovitskiy2020_vit.pdf
1512.03385|he2015_resnet.pdf
1905.11946|tan2019_efficientnet.pdf
2103.00020|radford2021_clip.pdf
2302.13971|touvron2023_llama.pdf
1910.10683|raffel2019_t5.pdf
2101.00027|gao2020_the_pile.pdf
2107.06499|lee2021_dedup.pdf
2305.16264|muennighoff2023_data_constrained.pdf
1902.10811|recht2019_imagenet_v2.pdf
2007.00644|taori2020_robustness.pdf
1912.11370|kolesnikov2019_bit.pdf
1805.00932|mahajan2018_weakly_supervised.pdf
1409.0575|russakovsky2014_ilsvrc.pdf
"

echo "$PAPERS" | while IFS='|' read -r id name; do
  [ -z "$id" ] && continue
  [ -s "raw/$name" ] && { echo "  have  $name"; continue; }
  echo "  fetch $name"
  curl -fsSL "https://arxiv.org/pdf/$id" -o "raw/$name" || echo "  !! failed $id"
  sleep 3
done

command -v python3 >/dev/null && python3 crux.py validate 2>/dev/null || true
