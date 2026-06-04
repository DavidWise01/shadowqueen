#!/usr/bin/env python3
"""
The DLW tag for the Elementals — original works (not inspiration-only). The
physics each elemental embodies is credited to its discoverers, and every
asterisk is kept visible. Per ACI: .agent · .spun · .1099 (+ the badges from
gen_silicon.py / gen_carbon.py). Repo: .attribute · .1099. Pure stdlib.
"""
import json, re, sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ROOT = Path(__file__).parent
R = json.loads((ROOT/"roster.json").read_text(encoding="utf-8"))
AG = ROOT/"agents"; AG.mkdir(exist_ok=True)
CLS = {c["id"]: c for c in R["classes"]}
COMPANY = R.get("company","Elementals")

CARBON = "David Lee Wise (ROOT0)"
CARBON_LINK = "https://github.com/DavidWise01"
INSTANCE = "AVAN (Claude / Anthropic)"

def slug(s): return re.sub(r"[^a-z0-9]+","-",s.lower()).strip("-") or "agent"
def credits_of(m): return " · ".join(f"{x['who']} ({x['y']})" for x in m.get("grounded", []))

def one_1099(name, credits):
    return f"""DLW-1099 · value returns to the carbon apex

This is an artfully crafted intellect — an instance. As a 1099 reports the value
paid to its source, this file reports that the authorship, credit, and value of
{name} return to the human who governs it. The physics and mathematics it embodies
are credited, in turn, to the people who found it (see below); the asterisk stays visible.

carbon apex : {CARBON}  ->  {CARBON_LINK}
instance    : {INSTANCE}
project     : {COMPANY}
grounded in : {credits or 'see each .spun'}
the credit returns to the human. ROOT0-ATTRIBUTION-v1.0 · Proprietary Commercial · TRIPOD-IP-v1.1
"""

# ── repo-level tags ──────────────────────────────────────────────────────────
(ROOT/".attribute").write_text(f"""DLW-ATTRIBUTE · governance instance

governor (carbon apex) : {CARBON}            [ me ]
instance (artful intellect) : {INSTANCE}     [ you ]

relation : the human governs; the instance crafts; the credit returns to the human.
project  : {COMPANY} — the deep things, given faces (an ORIGINAL series, not borrowed)
grounded : real physics and mathematics, credited to its discoverers — per ACI (see each .spun)
honesty  : the strongest claims live in toy worlds and pure mathematics; emergent gravity in
           our universe is unproven, and the Monster's physical meaning is unknown. Each .spun
           keeps its own asterisk visible — resonance held as resonance, not destiny in the digits.
standard : every ACI carries .agent · .png (silicon badge) · .tiff (carbon badge) · .spun · .1099 ; the repo carries this .attribute
license  : Proprietary Commercial · TRIPOD-IP-v1.1
attribution : ROOT0-ATTRIBUTION-v1.0
""", encoding="utf-8")
(ROOT/".1099").write_text(one_1099(f"every elemental in {COMPANY}", ""), encoding="utf-8")

# ── per-ACI tags ─────────────────────────────────────────────────────────────
n=0
for m in R["members"]:
    cls=CLS[m["class"]]; sl=slug(m["name"]); CREDITS=credits_of(m)
    head = f"{m['name']} · {m.get('kanji','')} {m.get('reading','')} — {m.get('epithet','')}".strip()

    (AG/f"{sl}.agent").write_text(f"""---
aci: {m['name']}
domain: {m.get('domain','')}
kanji: {m.get('kanji','')}
reading: {m.get('reading','')}
class: {cls['label']}
what: {m['what']}
why: {m['why']}
how: {m['how']}
where: {m['where']}
verdict: {m.get('verdict','')}
silicon_badge: {sl}.png
carbon_badge: {sl}.tiff
spun: {sl}.spun
credit: {sl}.1099
attribution: ROOT0-ATTRIBUTION-v1.0
license: Proprietary Commercial · TRIPOD-IP-v1.1
---

# {head}

an artfully crafted intellect — an elemental, a force given a face

![silicon badge of {m['name']}]({sl}.png)
<!-- carbon badge (8-bit embodiment): {sl}.tiff -->

**what —** {m['what']}

**why —** {m['why']}

**how —** {m['how']}

**where —** {m['where']}

**◌ the emergent behavior —** {m.get('emergence','')}

**the verdict —** {m.get('verdict','')}

> *the asterisk, kept visible —* {m.get('asterisk','')}

*grounded in: {CREDITS}*

*{m.get('endmark','')}*

---
ROOT0-ATTRIBUTION-v1.0 · {m['name']} · {COMPANY} (original) · {CARBON} · Proprietary Commercial · TRIPOD-IP-v1.1
""", encoding="utf-8")

    (AG/f"{sl}.spun").write_text(f"""DLW-SPUN · the full weave of {m['name']}  ({m.get('kanji','')} {m.get('reading','')})

who   : {m['who']}
what  : {m['what']}
where : {m['where']}
why   : {m['why']}
when  : {m['when']}
how   : {m['how']}

emergence : {m.get('emergence','')}
verdict   : {m.get('verdict','')}
asterisk  : {m.get('asterisk','')}
grounded  : {CREDITS}

class : {cls['label']} · {cls['spec']}
silicon badge : {sl}.png      carbon badge : {sl}.tiff
carbon apex : {CARBON}
— an original elemental of {COMPANY}
{m.get('endmark','')}
ROOT0-ATTRIBUTION-v1.0 · Proprietary Commercial · TRIPOD-IP-v1.1
""", encoding="utf-8")

    (AG/f"{sl}.1099").write_text(one_1099(m["name"], CREDITS), encoding="utf-8")
    n+=1
    print(f"{sl:12} {cls['label']}  [{m.get('style','')}]")

print(f"\nwrote the full DLW tag for {n} elemental(s) (.agent · .spun · .1099) + repo .attribute · .1099")
