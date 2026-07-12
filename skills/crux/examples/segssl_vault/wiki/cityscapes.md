---
type: wiki
title: Cityscapes Dataset
summary: Urban driving-scene segmentation benchmark (fine/coarse annotations, 19 classes) used both as an in-domain fine-tuning target and as the source-domain anchor for the ACDC domain-shift evaluation in SegSSL.
category: dataset
sources: raw/cordts2016_cityscapes.pdf
created: 2026-07-11
updated: 2026-07-11
---

# Cityscapes Dataset

Cityscapes provides 5,000 finely and 20,000 coarsely annotated street-scene images from 50 cities, deliberately recorded in clear weather, which sets both its label-density spectrum and its role as a clean-condition reference in later domain-shift work.

## Annotation protocol

Images come from a 22 cm-baseline stereo rig (2 MP CMOS sensors, 17 Hz, rolling shutter) yielding 16-bit HDR pairs plus tone-mapped 8-bit LDR RGB. Fine annotations cover 5,000 images (2,975 train / 500 val / 1,525 test, split at the city level) hand-drawn as layered polygons (LabelMe-style) on the 20th frame of a 30-frame snippet; each image took over 1.5 h including QC. Coarse annotations cover 20,000 additional images (one per 20 s or 20 m of driving across 23 cities), using looser polygons that trade boundary precision for speed. Fine annotations reach 9.43×10⁹ labeled pixels at 97.1% density; coarse annotations add 26.0×10⁹ pixels at 67.5% density — up to two orders of magnitude more annotated pixels than CamVid, DUS, or KITTI. Inter-annotator agreement on fine labels was measured at 96% (98% excluding void), and 97% of fine-labeled pixels received the same class when independently coarse-annotated, validating the coarse protocol as a cheap proxy for dense labels.

## Class taxonomy and metrics

30 visual classes are grouped into 8 categories (flat, construction, nature, vehicle, sky, object, human, void); classes too rare for reliable evaluation are dropped, leaving 19 classes for the benchmark. Standard pixel IoU (Jaccard index) is reported at both class and category granularity. Because IoU is biased toward large objects, Cityscapes also introduces instance-level IoU (iIoU), which reweights each pixel's contribution by the ratio of a class's average instance size to the size of its specific ground-truth instance, penalizing errors on small but important instances (e.g., distant pedestrians) that plain IoU would mask. The best baseline FCN-8s variant reached 67.1% IoU_class / 42.0% iIoU_class on the held-out test set.

## Dual role as fine-tuning target and domain-shift anchor

Because Cityscapes exposes both a small, precisely labeled fine split and a much larger, cheaply labeled coarse split, it is a natural testbed for [[label-efficiency]]: pretrained encoders paired with [[segmentation-decoders]] can be fine-tuned on varying fractions of the 2,975 fine images to measure how quickly performance saturates as dense annotation is added. Separately, because recordings deliberately excluded adverse weather such as heavy rain or snow, Cityscapes serves as the clean-weather source domain against which performance degradation on adverse-condition benchmarks like ACDC is measured — a role consistent with Cityscapes' own demonstrated cross-dataset transfer (an FCN trained only on Cityscapes outperformed specialized baselines on CamVid and KITTI without any target-domain fine-tuning).

## See also

Related:: [[label-efficiency]] [[segmentation-decoders]] [[overview]]
