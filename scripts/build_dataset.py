"""Build the merged municipal-waste dataset (12 material classes -> 4 SWM-2026 streams).

Sources (all public, downloaded from GitHub):
  - RealWaste   https://github.com/sam-single/realwaste            (CC BY-NC-SA 4.0)
  - TrashNet    https://github.com/garythung/trashnet               (MIT)
  - Garbage-12  Kaggle mostafaabla/garbage-classification, GitHub mirror
                https://github.com/arshpreet-nar/7TH-SEMESTER-PROJECT-
  - TrashBox    https://github.com/nikhilvenkatkumsetty/TrashBox (+ -testandvalid)

Steps: collect -> verify image opens -> exact (MD5) + perceptual (pHash) de-dup
       -> cap per class (priority: real-world sources first) -> resize -> stratified split.

Usage: python build_dataset.py --src <download dir> --out <output dir>
"""
import argparse, csv, hashlib, json, os, random
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps
import imagehash

SEED = 42
CAP_PER_CLASS = 2000
MAX_SIDE = 320
SPLIT = (0.70, 0.15, 0.15)
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# material class -> SWM Rules 2026 stream + disposal hint (used by backend/frontend)
CLASSES = {
    "cardboard":        ("dry",          "Flatten and keep dry; goes to the Material Recovery Facility (MRF)."),
    "paper":            ("dry",          "Keep clean and dry; recyclable at the MRF."),
    "plastic":          ("dry",          "Rinse, dry and put in the dry-waste bin for the MRF."),
    "metal":            ("dry",          "Rinse cans; recyclable metal for the MRF / kabadiwala."),
    "glass":            ("dry",          "Keep intact, wrap broken glass; dry-waste bin."),
    "textile":          ("dry",          "Donate if reusable, otherwise dry-waste bin."),
    "misc_trash":       ("dry",          "Non-recyclable dry reject; dry-waste bin."),
    "organic":          ("wet",          "Wet-waste bin; compost or bio-methanation."),
    "mask_glove":       ("sanitary",     "Wrap securely and store separately as sanitary waste."),
    "medicine_syringe": ("special_care", "Hand over only to authorised collection centres (special care)."),
    "battery":          ("special_care", "Never in regular bins; hand over to authorised collection centres."),
    "e_waste":          ("special_care", "Give to an authorised e-waste collector / MRF deposition point."),
}

# source priority: lower = kept first when capping (real-world photos preferred)
PRIORITY = {"realwaste": 0, "trashnet": 1, "garbage12": 2, "trashbox": 3}


def collect(src: Path):
    """Return list of (path, class, source, source_label)."""
    items = []

    def add_dir(d: Path, cls, source, label):
        if not d.exists():
            print("MISSING", d); return
        for p in d.rglob("*"):
            if p.suffix.lower() in IMG_EXT and p.is_file():
                items.append((str(p), cls, source, label))

    rw = src / "realwaste/RealWaste"
    for lab, cls in {"Cardboard": "cardboard", "Food Organics": "organic", "Glass": "glass",
                     "Metal": "metal", "Miscellaneous Trash": "misc_trash", "Paper": "paper",
                     "Plastic": "plastic", "Textile Trash": "textile", "Vegetation": "organic"}.items():
        add_dir(rw / lab, cls, "realwaste", lab)

    tn = src / "trashnet/dataset-resized"
    for lab, cls in {"cardboard": "cardboard", "glass": "glass", "metal": "metal",
                     "paper": "paper", "plastic": "plastic", "trash": "misc_trash"}.items():
        add_dir(tn / lab, cls, "trashnet", lab)

    g = src / "7TH-SEMESTER-PROJECT-/garbage_classification Dataset"
    for lab, cls in {"battery": "battery", "biological": "organic", "brown-glass": "glass",
                     "green-glass": "glass", "white-glass": "glass", "cardboard": "cardboard",
                     "clothes": "textile", "shoes": "textile", "metal": "metal", "paper": "paper",
                     "plastic": "plastic"}.items():
        # NOTE: Garbage-12 "trash" is excluded on purpose: it is dominated by face masks,
        # which would conflict with the mask_glove class.
        add_dir(g / lab, cls, "garbage12", lab)

    tb_dirs = [src / "TrashBox/TrashBox_train_dataset_subfolders",
               src / "TrashBox-testandvalid/TrashBox_testandvalid_dataset_subfolders"]
    for d in tb_dirs:
        for lab, cls in {"cardboard": "cardboard", "glass": "glass", "metal": "metal",
                         "paper": "paper", "plastic": "plastic", "e-waste": "e_waste"}.items():
            add_dir(d / lab, cls, "trashbox", lab)
    # medical sub-classes only exist in the train subfolders
    med = tb_dirs[0] / "medical"
    for sub, cls in {"gloves": "mask_glove", "masks": "mask_glove",
                     "medicines": "medicine_syringe", "syringe": "medicine_syringe"}.items():
        add_dir(med / sub, cls, "trashbox", f"medical/{sub}")
    return items


def fingerprint(path):
    try:
        with open(path, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            w, h = im.size
            if min(w, h) < 64:
                return path, None, None, "too_small"
            return path, md5, str(imagehash.phash(im)), None
    except Exception as e:  # corrupt / unreadable
        return path, None, None, f"error:{type(e).__name__}"


def save_resized(args):
    src, dst = args
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im.save(dst, "JPEG", quality=90, optimize=True)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    rng = random.Random(SEED)

    items = collect(src)
    print("collected", len(items), Counter(i[1] for i in items))
    meta = {i[0]: i for i in items}

    with ProcessPoolExecutor() as ex:
        fps = list(ex.map(fingerprint, [i[0] for i in items], chunksize=64))

    dropped = Counter()
    seen_md5, seen_phash = {}, {}
    kept = []
    # process in priority order so the real-world copy of a duplicate survives
    fps.sort(key=lambda r: (PRIORITY[meta[r[0]][2]], r[0]))
    for path, md5, ph, err in fps:
        if err:
            dropped[err.split(":")[0]] += 1; continue
        if md5 in seen_md5:
            dropped["dup_md5"] += 1; continue
        if ph in seen_phash:
            dropped["dup_phash"] += 1; continue
        seen_md5[md5] = path; seen_phash[ph] = path
        kept.append(meta[path])
    print("dropped", dict(dropped))

    by_cls = defaultdict(list)
    for it in kept:
        by_cls[it[1]].append(it)
    final = []
    for cls, lst in by_cls.items():
        rng.shuffle(lst)
        lst.sort(key=lambda it: PRIORITY[it[2]])  # stable: shuffled within source
        if len(lst) > CAP_PER_CLASS:
            # keep all real-world images, sample the rest uniformly
            real = [i for i in lst if i[2] in ("realwaste", "trashnet")]
            rest = [i for i in lst if i[2] not in ("realwaste", "trashnet")]
            lst = real + rng.sample(rest, CAP_PER_CLASS - len(real))
        final += lst

    # stratified split per class
    rows, jobs = [], []
    for cls in CLASSES:
        lst = [i for i in final if i[1] == cls]
        rng.shuffle(lst)
        n = len(lst); n_tr = round(n * SPLIT[0]); n_va = round(n * SPLIT[1])
        for k, it in enumerate(lst):
            split = "train" if k < n_tr else "val" if k < n_tr + n_va else "test"
            name = f"{cls}_{it[2]}_{k:05d}.jpg"
            dst = out / split / cls / name
            jobs.append((it[0], str(dst)))
            rows.append({"file": f"{split}/{cls}/{name}", "split": split, "class": cls,
                         "stream": CLASSES[cls][0], "source": it[2], "source_label": it[3],
                         "original_path": os.path.relpath(it[0], src)})
    with ProcessPoolExecutor() as ex:
        list(ex.map(save_resized, jobs, chunksize=64))

    with open(out / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    with open(out / "classes.json", "w") as f:
        json.dump({c: {"index": i, "stream": s, "disposal": d}
                   for i, (c, (s, d)) in enumerate(CLASSES.items())}, f, indent=2)
    stats = Counter((r["class"], r["split"]) for r in rows)
    src_stats = Counter((r["class"], r["source"]) for r in rows)
    with open(out / "stats.json", "w") as f:
        json.dump({"per_class_split": {f"{c}|{s}": n for (c, s), n in sorted(stats.items())},
                   "per_class_source": {f"{c}|{s}": n for (c, s), n in sorted(src_stats.items())},
                   "dropped": dict(dropped), "total": len(rows)}, f, indent=2)
    print("total", len(rows))


if __name__ == "__main__":
    main()
