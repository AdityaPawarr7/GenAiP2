"""Builds tools/human_coding.html: a blind hand-coding form (no notes, no Claude codes shown)."""
import json, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
SLUGS = ["berkeley", "cmu", "columbia", "nyu", "williams"]
def sections(slug):
    txt = (ROOT / "data/raw" / f"{slug}.md").read_text(encoding="utf-8")
    name = txt.splitlines()[0].lstrip("# ").strip()
    out = []
    for block in re.split(r"^## ", txt, flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        if head.strip() == "notes":
            continue  # notes are never evidence; hidden to keep coding blind
        out.append({"section": head.strip(), "body": body.strip()})
    return {"slug": slug, "name": name, "sections": out}
data = [sections(s) for s in SLUGS]
html = (ROOT / "tools/human_coding.template.html").read_text(encoding="utf-8")
(ROOT / "tools/human_coding.html").write_text(html.replace("/*DATA*/[]", json.dumps(data)), encoding="utf-8")
print("wrote tools/human_coding.html for", SLUGS)
