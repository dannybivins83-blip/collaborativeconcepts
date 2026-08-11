"""Seed taxonomy.

Deliberately shallow and small at v1. A taxonomy is only useful if every tag in
it is one a human would defend, and every alias is one that does not produce
false positives. Growth happens through the `create-tag` skill with evidence,
not by bulk-importing a keyword list.

Shape: (slug, display name, [aliases], [children])
"""

TAXONOMY = [
    ("technology", "Technology", [], [
        ("artificial-intelligence", "Artificial Intelligence",
         ["AI", "artificial intelligence", "machine learning", "deep learning"], [
            ("generative-ai", "Generative AI",
             ["generative AI", "large language model", "LLM", "foundation model"], []),
            ("gpus", "GPUs",
             ["GPU", "graphics processing unit", "accelerated computing"], []),
            ("ai-infrastructure", "AI Infrastructure",
             ["AI infrastructure", "AI supercomputer", "training cluster"], []),
            ("ai-software", "AI Software",
             ["AI software", "CUDA", "inference software"], []),
            ("ai-data-centers", "AI Data Centers",
             ["AI data center", "AI data centre", "hyperscale data center"], []),
         ]),
        ("data-centers", "Data Centers",
         ["data center", "data centre", "hyperscaler", "colocation"], []),
        ("semiconductors", "Semiconductors",
         ["semiconductor", "chip", "wafer", "foundry", "fab"], []),
        ("cloud-computing", "Cloud Computing",
         ["cloud computing", "public cloud", "hybrid cloud"], []),
        ("robotics", "Robotics", ["robotics", "robot", "automation"], []),
        ("autonomous-vehicles", "Autonomous Vehicles",
         ["autonomous vehicle", "self-driving", "autonomous driving", "ADAS"], []),
        ("cybersecurity", "Cybersecurity",
         ["cybersecurity", "cyber attack", "ransomware", "zero trust"], []),
    ]),
    ("energy", "Energy", [], [
        ("nuclear-power", "Nuclear Power",
         ["nuclear power", "nuclear energy", "SMR", "small modular reactor"], []),
        ("solar", "Solar", ["solar power", "photovoltaic", "solar panel"], []),
        ("grid", "Grid & Power Demand",
         ["power demand", "grid capacity", "electricity demand", "power purchase agreement"], []),
    ]),
    ("healthcare", "Healthcare", [], [
        ("glp-1", "GLP-1 Drugs",
         ["GLP-1", "semaglutide", "tirzepatide", "obesity drug", "weight loss drug"], []),
        ("medical-devices", "Medical Devices", ["medical device", "implantable"], []),
    ]),
    ("consumer", "Consumer", [], [
        ("footwear", "Footwear", ["footwear", "sneaker", "running shoe"], []),
        ("athletic-apparel", "Athletic Apparel",
         ["athletic apparel", "activewear", "performance apparel"], []),
        ("e-commerce", "E-Commerce", ["e-commerce", "ecommerce", "online sales"], []),
    ]),
    ("financial", "Financial", [], [
        ("crypto", "Crypto Assets",
         ["cryptocurrency", "bitcoin", "digital asset", "blockchain"], []),
        ("payments", "Payments", ["payments", "payment processing", "interchange"], []),
    ]),
    ("industrial", "Industrial", [], [
        ("defense", "Defense", ["defense", "defence", "munitions", "military contract"], []),
        ("supply-chain", "Supply Chain",
         ["supply chain", "supplier constraint", "lead time", "backlog"], []),
    ]),
    ("risk", "Risk Language", [], [
        # Filing-diff signals lean on these; they're risk vocabulary, not themes.
        ("export-controls", "Export Controls",
         ["export control", "export restriction", "entity list", "trade restriction"], []),
        ("customer-concentration", "Customer Concentration",
         ["customer concentration", "significant customer", "one customer accounted"], []),
        ("capacity-constraints", "Capacity Constraints",
         ["capacity constraint", "supply constraint", "unable to meet demand"], []),
    ]),
]


def seed_taxonomy(db, taxonomy=None):
    """Idempotently create the tag tree + aliases. Safe to re-run."""
    from packages.database import repositories as repo

    created = 0

    def walk(nodes, parent_id=None, category=None):
        nonlocal created
        for slug, name, aliases, children in nodes:
            tag_id = f"tag_{slug}"
            repo.upsert_tag(db, tag_id=tag_id, name=name, slug=slug,
                            parent_id=parent_id, category=category or slug)
            for alias in set(aliases) | {name}:
                repo.add_tag_alias(db, tag_id, alias)
            created += 1
            walk(children, parent_id=tag_id, category=category or slug)

    walk(taxonomy or TAXONOMY)
    db.commit()
    return created


def tag_path(db, tag_id):
    """Root-to-leaf path, e.g. ['Technology', 'Artificial Intelligence', 'GPUs']."""
    path, seen = [], set()
    current = tag_id
    while current and current not in seen:
        seen.add(current)
        row = db.one("SELECT id, name, parent_id FROM tags WHERE id=?", (current,))
        if not row:
            break
        path.append(row["name"])
        current = row["parent_id"]
    return list(reversed(path))
