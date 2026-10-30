"""Self-check for the spike: every text slot sits inside its ratio's safe area and headlines stay readable.
Run:  .venv/Scripts/python.exe spike/test_block.py
"""
import block as b

TEXTS = {"headline": "SOLD — TWICE", "number": "×2", "label": "THE EIFFEL TOWER"}

for ratio, r in b.RATIOS.items():
    x0, y0, x1, y1 = r["safe"]
    for arch, slots in b.SLOTS.items():
        for name in slots[ratio]:
            rect = b.slot_rect(ratio, arch, name)
            assert x0 <= rect.left() and rect.right() <= x1 and y0 <= rect.top() and rect.bottom() <= y1, (ratio, arch, name)
    size = b.fit_size(b.HEAD_TF, TEXTS["headline"], b.slot_rect(ratio, "headline_photo", "headline"))
    assert size >= b.MIN_HEADLINE_PX[ratio], f"{ratio} headline {size:.0f}px < {b.MIN_HEADLINE_PX[ratio]}px"
    print(f"{ratio}: all slots inside safe area, headline {size:.0f}px")

for ease in (b.out_cubic, b.back_out, b.bounce_out):
    assert abs(ease(0)) < 1e-9 and abs(ease(1) - 1) < 1e-9, ease.__name__
print("easings start at 0 and land on 1")
print("ALL CHECKS PASSED")
