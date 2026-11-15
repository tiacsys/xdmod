"""Variant rules on the model JSON (D102, D105, D135; variants.md §3). Check CK-B4.

Port of the research prototype build/research-vamos/tools/variant_check.py. The model uses
SysML v2 variation/variant for the 150 % product architecture and PLEML (#featureModel,
#featureTree, #feature, #featureConfiguration, #FeatureBinding, @FCFGB) for features.

Iteration 1 subset (D135):
  F1  a configuration sets only features of its tree; every feature group keeps its multiplicity
  F2  every requires / xor / implies constraint holds in every configuration
  V1  every product model (@FCFGB) names an existing configuration, and every configuration has
      exactly one product model
  V2  the product model binds every variation of the 150 % model ...
  V3  ... to one of that variation's own variants
  V4  the chosen variant is enabled: all features it is bound to are chosen (several bindings = AND)
  V5  exactly one variant of each variation is enabled per configuration
Not yet: V6 (assert constraints per product model), T1-T3 (iteration 2).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from curatrix.model import Model


@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    configs: dict[str, set[str]] = field(default_factory=dict)
    variations: dict[str, list[str]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        return (f"variant-check: {'OK' if self.ok else 'FAILED'} ({len(self.errors)} errors, "
                f"{len(self.configs)} configurations, {len(self.variations)} variations)")


def short(q: str) -> str:
    return q.split("::")[-1]


def check(m: Model) -> Result:
    E = m.e
    res = Result()
    err = res.errors.append

    def g(r):
        return m.get(r) if isinstance(r, dict) and r else None

    qn = Model.qn

    def owned(p):
        yield from m.owned(p)

    def meta_names(p):
        return [qn(g(x.get("metadataDefinition"))) for _, x in owned(p) if x["@type"] == "MetadataUsage"]

    def walk(p):
        yield from m.walk(p)

    def mult(p):
        """(lower, upper) of the owned multiplicity, or None. upper None = *."""
        for _, x in owned(p):
            if x["@type"] == "MultiplicityRange":
                vals = [b.get("value") if b["@type"] == "LiteralInteger" else None for _, b in owned(x)]
                if len(vals) == 1:
                    return (vals[0] if vals[0] is not None else 0, vals[0])
                if len(vals) >= 2:
                    return (vals[0], vals[1])
        return None

    def redefined(p):
        for r in p.get("ownedRelationship", []) or []:
            rel = g(r)
            if rel and rel["@type"] == "Redefinition":
                return qn(g(rel.get("redefinedFeature")))
        return None

    def subsetted(p):
        out = []
        for r in p.get("ownedRelationship", []) or []:
            rel = g(r)
            if rel and rel["@type"] == "Subsetting":
                out.append(qn(g(rel.get("subsettedFeature"))))
        return out

    def refs_in(p):
        return [qn(g(x.get("referent"))) for x in walk(p) if x["@type"] == "FeatureReferenceExpression"]

    # ---- feature trees
    trees = [p for p in E.values() if not p.get("isLibraryElement") and p.get("owningType")
             and "PLEML::FeatureTreeMetadata" in meta_names(p)]
    features: dict[str, dict] = {}
    for t in trees:
        for _, f in owned(t):
            if "PLEML::FeatureMetadata" not in meta_names(f):
                continue
            info = {"mult": mult(f), "parents": [s for s in subsetted(f) if s.startswith(qn(t))], "constraints": []}
            for _, c in owned(f):
                if c["@type"] != "AssertConstraintUsage":
                    continue
                kind = (redefined(c) or "").split("::")[-1]   # requiresFeatures / xorFeatures / impliesFeatures
                ops = {}
                for x in walk(c):
                    if x["@type"] == "Feature" and x.get("name") in ("operandA", "operandB"):
                        ops[x["name"]] = [qn(f) if r == "Base::things::that" else r for r in refs_in(x)]
                info["constraints"].append((kind, ops.get("operandA", []), ops.get("operandB", [])))
            features[qn(f)] = info

    # ---- feature configurations
    configs: dict[str, set[str]] = {}
    for p in E.values():
        if p.get("isLibraryElement") or p["@type"] != "OccurrenceUsage":
            continue
        if "PLEML::FeatureConfigurationMetadata" not in meta_names(p):
            continue
        sel = set()
        for _, f in owned(p):
            rf = redefined(f)
            if rf is None:
                continue
            if rf not in features:
                err(f"F1 {p.get('name')}: '{short(rf)}' is not a feature of the tree")
                continue
            mm = mult(f)
            if mm and mm[0] and mm[0] >= 1:
                sel.add(rf)
        configs[p.get("name")] = sel
    res.configs = configs

    children = defaultdict(list)
    for fq, info in features.items():
        for par in info["parents"]:
            children[par].append(fq)
    for cname, sel in configs.items():
        for grp, kids in children.items():          # F1 group multiplicity
            n = sum(1 for k in kids if k in sel)
            lo, hi = features[grp]["mult"] or (0, None)
            lo = lo or 0
            if grp in sel or lo >= 1:
                if n < max(lo, 1) or (hi is not None and n > hi):
                    err(f"F1 {cname}: group '{short(grp)}' has {n} selected children, "
                        f"allowed {lo}..{hi if hi is not None else '*'}")
        for fq, info in features.items():           # F2 constraints
            for kind, a, b in info["constraints"]:
                if kind == "requiresFeatures" and fq in sel and not all(x in sel for x in b):
                    err(f"F2 {cname}: '{short(fq)}' requires {[short(x) for x in b]}")
                if kind == "xorFeatures" and fq in sel and any(x in sel for x in b):
                    err(f"F2 {cname}: '{short(fq)}' excludes {[short(x) for x in b]}")
                if kind == "impliesFeatures" and all(x in sel for x in a) and not all(x in sel for x in b):
                    err(f"F2 {cname}: ({' and '.join(short(x) for x in a)}) implies {[short(x) for x in b]}")

    # ---- feature bindings (#FeatureBinding dependency from <asset> to <feature>)
    bound: dict[str, set[str]] = defaultdict(set)
    for p in E.values():
        if p["@type"] != "Dependency" or p.get("isLibraryElement"):
            continue
        is_fb = "PLEML::FeatureBinding" in meta_names(p)
        for a in p.get("ownedAnnotation", []) or []:
            ann = g(a)
            if ann and (qn(g(ann.get("annotatingElement"))) == "PLEML::FeatureBinding"
                        or "PLEML::FeatureBinding" in [qn(g((g(ann.get("annotatingElement")) or {}).get("metadataDefinition")))]):
                is_fb = True
        if is_fb:
            for c in p.get("client", []) or []:
                for s in p.get("supplier", []) or []:
                    bound[qn(g(c))].add(qn(g(s)))
    if not bound:   # fallback (prototype behaviour): any dependency into a feature tree
        for p in E.values():
            if p["@type"] == "Dependency" and not p.get("isLibraryElement"):
                for c in p.get("client", []) or []:
                    for s in p.get("supplier", []) or []:
                        if qn(g(s)) in features:
                            bound[qn(g(c))].add(qn(g(s)))

    def enabled(asset, sel):
        fs = bound.get(asset)
        return True if not fs else fs <= sel

    # ---- variations of the 150 % model
    variants: dict[str, list[str]] = defaultdict(list)
    for p in E.values():
        if p["@type"] == "VariantMembership" and not p.get("isLibraryElement"):
            vn = qn(g(p.get("membershipOwningNamespace")))
            if vn.startswith("PLEML::"):
                continue
            variants[vn].append(qn(g(p.get("ownedVariantUsage"))))
    res.variations = dict(variants)

    # ---- product models (@FCFGB)
    models_per_config: dict[str, list[str]] = defaultdict(list)
    for p in E.values():
        if p["@type"] != "Package" or p.get("isLibraryElement"):
            continue
        cfg = None
        for _, x in owned(p):
            if x["@type"] == "MetadataUsage" and qn(g(x.get("metadataDefinition"))) == "PLEML::FeatureConfigurationBinding":
                for y in walk(x):
                    if y["@type"] == "LiteralString":
                        cfg = y["value"]
        if cfg is None:
            continue
        if cfg not in configs:
            err(f"V1 {p.get('name')}: feature configuration '{cfg}' does not exist")
            continue
        models_per_config[cfg].append(p.get("name"))
        sel = configs[cfg]
        for _, pd in owned(p):
            if pd["@type"] != "PartDefinition":
                continue
            bases = []
            for r in pd.get("ownedRelationship", []) or []:
                rel = g(r)
                if rel and rel["@type"] == "Subclassification":
                    bases.append(qn(g(rel.get("superclassifier"))))
            binds = {}
            for _, f in owned(pd):
                rf = redefined(f)
                if rf:
                    binds[rf] = refs_in(f)
            for vn, vs in sorted(variants.items()):
                if not any(vn.startswith(b + "::") for b in bases):
                    continue
                en = [v for v in vs if enabled(v, sel)]
                if len(en) != 1:
                    err(f"V5 {pd.get('name')} ({cfg}): variation '{short(vn)}' has {len(en)} enabled variants "
                        f"{[short(v) for v in en]}")
                if vn not in binds or not binds[vn]:
                    err(f"V2 {pd.get('name')} ({cfg}): variation '{short(vn)}' is not bound")
                    continue
                choice = binds[vn][0]
                if choice not in vs:
                    err(f"V3 {pd.get('name')} ({cfg}): '{short(vn)}' is bound to '{short(choice)}', which is not "
                        f"one of its variants {[short(v) for v in vs]}")
                elif not enabled(choice, sel):
                    err(f"V4 {pd.get('name')} ({cfg}): variant '{short(choice)}' needs features "
                        f"{[short(x) for x in sorted(bound[choice])]}, not all selected")
                else:
                    res.notes.append(f"ok  {pd.get('name')} ({cfg}): {short(vn)} = {short(choice)}")
    if models_per_config or variants:   # V1, second half: one product model per configuration
        for cname in sorted(configs):
            n = len(models_per_config.get(cname, []))
            if n != 1:
                err(f"V1 configuration '{cname}' has {n} product models {sorted(models_per_config.get(cname, []))}")

    # ---- requirement applicability (report)
    reqs = sorted(q for q in bound if any(p.get("qualifiedName") == q and p["@type"] == "RequirementUsage"
                                          for p in E.values()))
    for cname, sel in sorted(configs.items()):
        res.notes.append(f"cfg {cname}: features {sorted(short(x) for x in sel)}")
        for r in reqs:
            res.notes.append(f"    requirement {short(r)} applies: {enabled(r, sel)}")
    return res
