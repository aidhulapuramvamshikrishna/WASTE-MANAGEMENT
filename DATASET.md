# Dataset: Municipal Waste (12 material classes → 4 SWM-2026 streams)

Built by `scripts/build_dataset.py` from four public datasets.
Location: `data/processed/waste12/` (`train/`, `val/`, `test/`, one folder per class), so it loads directly with `torchvision.datasets.ImageFolder`.

## Summary
- **18,951 images**, 12 classes, stratified split **70 / 15 / 15** (seed 42)
- Images resized so the longest side is ≤ 320 px (JPEG q90). Train at 224×224 with `RandomResizedCrop`.
- 4,115 duplicates removed (3,754 exact MD5, 361 perceptual-hash near-duplicates). When the same image appeared in several datasets, the real-world copy (RealWaste/TrashNet) was kept. Removing these keeps near-identical images from landing in both train and test.
- 8 broken or tiny images removed.
- Classes are capped at 2,000 images. All RealWaste and TrashNet images were kept; web-scraped images were sampled to fill the rest.

| Class | Stream (SWM Rules 2026) | Train | Val | Test | Total | Sources |
|---|---|---|---|---|---|---|
| cardboard | dry | 1400 | 300 | 300 | 2000 | RealWaste, TrashNet, Garbage-12, TrashBox |
| paper | dry | 1400 | 300 | 300 | 2000 | RealWaste, TrashNet, Garbage-12, TrashBox |
| plastic | dry | 1400 | 300 | 300 | 2000 | RealWaste, TrashNet, Garbage-12, TrashBox |
| metal | dry | 1400 | 300 | 300 | 2000 | RealWaste, TrashNet, Garbage-12, TrashBox |
| glass | dry | 1400 | 300 | 300 | 2000 | RealWaste, TrashNet, Garbage-12 (3 glass colours), TrashBox |
| textile | dry | 1400 | 300 | 300 | 2000 | RealWaste Textile, Garbage-12 clothes + shoes |
| misc_trash | dry (non-recyclable reject) | 442 | 95 | 95 | 632 | RealWaste Misc. Trash, TrashNet trash |
| organic | wet | 1280 | 274 | 274 | 1828 | RealWaste Food Organics + Vegetation, Garbage-12 biological |
| mask_glove | sanitary | 524 | 112 | 113 | 749 | TrashBox medical/masks + gloves |
| medicine_syringe | special care | 561 | 120 | 120 | 801 | TrashBox medical/medicines + syringe |
| battery | special care | 659 | 141 | 141 | 941 | Garbage-12 battery |
| e_waste | special care | 1400 | 300 | 300 | 2000 | TrashBox e-waste (cables, chips, phones, laptops, small appliances) |

Files:
- `manifest.csv`: one row per image with split, class, stream, source dataset, original label and original path.
- `classes.json`: class index, stream and disposal advice. The backend and frontend use this to turn a material prediction into a stream.
- `stats.json`: counts per class/split, per class/source, and the de-duplication log.

## Known limitations (state these in the report)
1. **Sanitary stream is only partly covered.** No public, GitHub-hosted dataset of diapers or sanitary napkins exists. `mask_glove` (used masks and gloves) stands in for it. Improvement: photograph your own sanitary items (wrapped), or download a CC BY 4.0 Roboflow sanitary-pad set manually and add it as a new class.
2. **Domain mix.** RealWaste (landfill) and TrashNet (white background) are real photos. Garbage-12 and TrashBox are web-scraped, and some carry stock-photo watermarks. Report test accuracy **per source** (from `manifest.csv`) as well as overall. Real-world photos usually score lower.
3. **Class imbalance.** The smallest class (misc_trash, 632) is about 3× smaller than the largest (2,000). Use class-weighted cross-entropy or a weighted sampler, and report macro-F1, not just accuracy.
4. **Garbage-12 "trash" was excluded on purpose**: it is mostly face masks, which would conflict with `mask_glove`.
5. **Expected confusions:** plastic ↔ glass (transparent items), paper ↔ cardboard, misc_trash ↔ everything.

## Sources and licences (cite all in the report)
| Dataset | Link | Licence |
|---|---|---|
| RealWaste: Single, Iranmanesh & Raad (2023), *Information* 14(12):633, doi:10.3390/info14120633 | https://github.com/sam-single/realwaste | CC BY-NC-SA 4.0 (non-commercial; fine for academic use) |
| TrashNet: Yang & Thung (2016), Stanford CS229 | https://github.com/garythung/trashnet | MIT |
| Garbage Classification (12 classes): M. Mohamed (Kaggle, 2021) | Kaggle `mostafaabla/garbage-classification`, via the GitHub mirror https://github.com/arshpreet-nar/7TH-SEMESTER-PROJECT- | See the Kaggle page (ODbL) |
| TrashBox: Kumsetty et al. (2022), IEEE FRUCT-31, "TrashBox: Trash Detection and Classification using Quantum Transfer Learning" | https://github.com/nikhilvenkatkumsetty/TrashBox and `TrashBox-testandvalid` | Cite the IEEE paper as the authors request |

Licence note: because of RealWaste's NC-SA terms, this merged dataset and models trained on it are for **non-commercial academic use**.

## Rebuild
```bash
# clone the four repos into <src>, unzip trashnet/data/dataset-resized.zip to <src>/trashnet/
pip install pillow imagehash
python scripts/build_dataset.py --src <src> --out data/processed/waste12
```
