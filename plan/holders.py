"""
Holder definitions for the studio revamp - one PEGBOARDLAB parameter set
per tool, sized from the photos of 2026-11-05 and the products' real
dimensions. Every holder is two-part (spine + holder, Ø3.5 × 15
countersunk drywall screws), labelled on its flange, designed for a
support-free print on the H2S in ABS-GF.

    id        short code (board letter · zone · index)
    item      what it holds, qty = how many of the tool
    n         how many holders to print
    params    overrides on PEGBOARDLAB defaults (board applied first)

Board A = imperial 19 mm (studs Ø7.8, screws into the studs).
Board C / B = metric 4 mm (J-hook mounts; screws bite the panel between holes).
"""

A = "imperial_19"
MET = "metric_4"

TWO = dict(split="two", brand_src="text", brand_font="sans", brand_bold=True, brand_mode="recess",
           brand_depth=0.5, brand_size=0.0, mt_margin=7.0)
JH = dict(mt_fix="jhook", mt_pattern="2V")        # metric default mount: rolled J on the top hole, stop below


def H(id_, item, brand, zone, board, n, text, **params):
    p = dict(TWO)
    p.update(params)
    p["brand_text"] = text
    return dict(id=id_, item=item, brand=brand, zone=zone, board=board, n=n, params=p)


HOLDERS = [
    # ------------------------------------------------------------ A · zone 1  clamps · square · bag
    H("A1-01", "Tool bag", "Bosch", 1, A, 1, "BOSCH BAG", family="hook", hk_type="j", hk_w=32, hk_reach=42, hk_t=7, hk_tip=22, hk_rib=14, hk_ph=92, mt_pattern="grid", mt_cols=1, mt_rows=3),
    H("A1-02", "End nippers", "—", 1, A, 1, "NIPPERS", family="hook", hk_type="j", hk_w=20, hk_reach=35, hk_t=6, hk_tip=12, hk_ph=70, mt_pattern="2V"),
    H("A1-03", "Spring clamps L ×2", "Irwin", 1, A, 1, "IRWIN L", family="hook", hk_type="peg", hk_w=72, hk_reach=50, hk_t=10, hk_tip=8, hk_rib=0, hk_ph=48, mt_pattern="2H"),
    H("A1-04", "Spring clamps S ×2", "Irwin", 1, A, 1, "IRWIN S", family="hook", hk_type="peg", hk_w=60, hk_reach=45, hk_t=8, hk_tip=8, hk_rib=0, hk_ph=48, mt_pattern="2H"),
    H("A1-05", "Combination square", "Irwin", 1, A, 1, "SQUARE", family="hook", hk_type="j", hk_w=30, hk_reach=35, hk_t=6, hk_tip=10, hk_ph=70, mt_pattern="2V"),
    # ------------------------------------------------------------ A · zone 2  Bosch 12V
    H("A2-01", "GWS 12V-76 grinder", "Bosch", 2, A, 1, "GWS 12V", family="holster", hs_type="saddle", hs_inner_w=44, hs_inner_d=60, hs_arm=10, hs_h=35, hs_r=8, hs_flare=3, hs_ph=72, mt_pattern="4"),
    H("A2-02", "Drill bit case", "Bosch", 2, A, 1, "BITS", family="tray", tr_type="tray", tr_w=172, tr_depth=42, tr_h=30, tr_wall=2.4, tr_floor=3, tr_r=4, tr_ph=48, mt_pattern="row"),
    H("A2-03", "GKS 12V-26 circular saw", "Bosch", 2, A, 1, "GKS 12V", family="holster", hs_type="saddle", hs_inner_w=52, hs_inner_d=75, hs_arm=12, hs_h=40, hs_r=10, hs_flare=3, hs_ph=72, mt_pattern="4"),
    H("A2-04", "Bits · small parts box", "Bosch", 2, A, 1, "SMALL", family="tray", tr_type="tray", tr_w=80, tr_depth=36, tr_h=25, tr_wall=2.0, tr_floor=3, tr_ph=48, mt_pattern="2H"),
    H("A2-05", "Accessory box", "Bosch", 2, A, 1, "L-BOXX", family="tray", tr_type="tray", tr_w=215, tr_depth=66, tr_h=30, tr_wall=2.4, tr_floor=3, tr_ph=48, mt_pattern="row"),
    H("A2-06", "Glue pen", "Bosch", 2, A, 1, "GLUE PEN", family="holster", hs_type="saddle", hs_inner_w=38, hs_inner_d=50, hs_arm=8, hs_h=28, hs_r=6, hs_flare=2, hs_ph=94, mt_pattern="grid", mt_cols=1, mt_rows=3),
    H("A2-07", "GSR 12V-35 drill", "Bosch", 2, A, 1, "GSR 12V", family="holster", hs_type="saddle", hs_inner_w=44, hs_inner_d=62, hs_arm=10, hs_h=35, hs_r=8, hs_flare=3, hs_ph=72, mt_pattern="4"),
    H("A2-08", "GRO 12V-35 rotary", "Bosch", 2, A, 1, "GRO 12V", family="holster", hs_type="ring", hs_ring_d=34, hs_arm=8, hs_h=25, hs_flare=2, hs_ph=72, mt_pattern="4"),
    # ------------------------------------------------------------ A · zone 3  Irwin hand tools
    H("A3-01", "Chisels ×3 + gouge", "Irwin", 3, A, 1, "IRWIN CHISELS", family="rack", rk_type="chisels", rk_n=4, rk_d=28, rk_slot_t=6, rk_pitch=40, rk_depth=36, rk_t=8, rk_margin=6, rk_ph=48, mt_pattern="row"),
    H("A3-02", "Screwdrivers ×2 + spare", "Irwin", 3, A, 1, "IRWIN DRIVERS", family="rack", rk_type="drivers", rk_n=3, rk_d=9, rk_pitch=40, rk_depth=32, rk_t=8, rk_margin=8, rk_ph=48, mt_pattern="row"),
    H("A3-03", "Marking knife · sheath", "—", 3, A, 1, "KNIFE", family="hook", hk_type="j", hk_w=25, hk_reach=30, hk_t=6, hk_tip=10, hk_ph=70, mt_pattern="2V"),
    # ------------------------------------------------------------ A · zone 4  Wera · drive · level
    H("A4-01", "Tool-Check Plus", "Wera", 4, A, 1, "TOOL-CHECK", family="tray", tr_type="tray", tr_w=200, tr_depth=48, tr_h=18, tr_wall=2.4, tr_floor=3, tr_ph=48, mt_pattern="row"),
    H("A4-02", "Ratchet", "Wera", 4, A, 1, "RATCHET", family="hook", hk_type="j", hk_w=16, hk_reach=30, hk_t=6, hk_tip=10, hk_ph=70, mt_pattern="2V"),
    H("A4-03", "Hex keys ×9", "Wera", 4, A, 1, "HEX-PLUS", family="rack", rk_type="hexkeys", rk_pitch=14, rk_depth=26, rk_t=10, rk_margin=6, rk_ph=48, mt_pattern="row"),
    H("A4-04", "Laser level", "—", 4, A, 1, "LASER", family="tray", tr_type="tray", tr_w=112, tr_depth=112, tr_h=12, tr_wall=2.4, tr_floor=3, tr_ph=48, mt_pattern="row"),
    H("A4-05", "Future Wera drivers ×6 (spare)", "Wera", 4, A, 1, "WERA", family="rack", rk_type="drivers", rk_n=6, rk_d=10, rk_pitch=24, rk_depth=32, rk_t=8, rk_margin=8, rk_ph=48, mt_pattern="row"),
    H("A4-06", "Spare quickdraw J ×2", "—", 4, A, 2, "SPARE", family="hook", hk_type="j", hk_w=20, hk_reach=35, hk_t=6, hk_tip=12, hk_ph=70, mt_pattern="2V"),
    # ------------------------------------------------------------ A · zone 6  cut · grip · power   (rows 24-36)
    H("A6-01", "Pliers ×6 + crimper slot", "—", 6, A, 1, "PLIERS", family="rack", rk_type="chisels", rk_n=7, rk_d=28, rk_slot_t=14, rk_pitch=36, rk_depth=42, rk_t=10, rk_margin=6, rk_ph=48, mt_pattern="row"),
    H("A6-02", "Aviation snips", "—", 6, A, 1, "SNIPS", family="hook", hk_type="j", hk_w=25, hk_reach=35, hk_t=6, hk_tip=12, hk_ph=70, mt_pattern="2V"),
    H("A6-03", "Scissors", "—", 6, A, 1, "SCISSORS", family="hook", hk_type="j", hk_w=20, hk_reach=30, hk_t=6, hk_tip=10, hk_ph=70, mt_pattern="2V"),
    H("A6-04", "Wrenches: adjustable + spanner + spare", "—", 6, A, 1, "WRENCHES", family="rack", rk_type="wrenches", rk_n=3, rk_d=14, rk_pitch=30, rk_depth=42, rk_t=10, rk_slot_len=28, rk_margin=6, rk_ph=48, mt_pattern="row"),
    H("A6-05", "Work light tube Ø50 × 300", "—", 6, A, 1, "LIGHT", family="hook", hk_type="double", hk_gap=236, hk_prong=20, hk_reach=55, hk_t=6, hk_tip=16, hk_rib=0, hk_ph=48, mt_pattern="row"),
    H("A6-06", "Multitool (stands)", "—", 6, A, 1, "MULTI", family="tray", tr_type="cup", tr_w=42, tr_depth=24, tr_h=50, tr_wall=2.0, tr_floor=3, tr_r=3, tr_ph=48, mt_pattern="2V"),
    H("A6-07", "Spare knife / cutter J ×2", "—", 6, A, 2, "SPARE", family="hook", hk_type="j", hk_w=20, hk_reach=30, hk_t=6, hk_tip=10, hk_ph=70, mt_pattern="2V"),
    # ------------------------------------------------------------ A · zone 5  measure · mark  (rows 36-45, nearest the bench)
    H("A5-01", "Steel rules 150 · 300", "—", 5, A, 1, "RULES", family="magstrip", mg_w=40, mg_h=160, mg_mode="embed", mg_n=1, mg_rows=4, mg_size="10x3", mg_cover=0.6, plate_t=6, mt_pattern="col"),
    H("A5-02", "Digital caliper 150", "—", 5, A, 1, "CALIPER", family="holster", hs_type="saddle", hs_inner_w=18, hs_inner_d=26, hs_arm=7, hs_h=30, hs_r=3, hs_flare=2, hs_ph=94, mt_pattern="grid", mt_cols=1, mt_rows=3),
    H("A5-03", "Micrometer 0-25", "—", 5, A, 1, "MICRO", family="hook", hk_type="j", hk_w=20, hk_reach=30, hk_t=6, hk_tip=10, hk_ph=70, mt_pattern="2V"),
    H("A5-04", "Protractor", "—", 5, A, 1, "PROTRACTOR", family="hook", hk_type="j", hk_w=20, hk_reach=30, hk_t=6, hk_tip=10, hk_ph=70, mt_pattern="2V"),
    H("A5-05", "Scriber · feelers · punches", "—", 5, A, 1, "SCRIBE", family="rack", rk_type="drivers", rk_n=4, rk_d=8, rk_pitch=18, rk_depth=26, rk_t=8, rk_margin=6, rk_ph=48, mt_pattern="2H"),
    H("A5-06", "Tape measure 8 m", "Stanley", 5, A, 1, "TAPE", family="holster", hs_type="saddle", hs_inner_w=46, hs_inner_d=78, hs_arm=8, hs_h=35, hs_r=8, hs_flare=3, hs_ph=70, mt_pattern="4"),
    H("A5-07", "Pens · markers ×8", "—", 5, A, 1, "PENS", family="rack", rk_type="sockets", rk_n=4, rk_rows=2, rk_d=18, rk_pitch=23, rk_depth=52, rk_t=14, rk_pocket=12, rk_margin=5, rk_ph=48, mt_pattern="row"),
    H("A5-08", "Test leads · cables", "—", 5, A, 1, "LEADS", family="clip", cl_type="snap", cl_n=3, cl_d=5, cl_wall=2, cl_snap=0.6, cl_len=24, cl_ph=96, mt_pattern="grid", mt_cols=1, mt_rows=3),
    # ------------------------------------------------------------ A · zone labels
    H("A0-01", "Zone label plates ×6", "mdrn", 0, A, 6, "ZONE", family="plate", pl_w=120, pl_h=28, plate_t=4, brand_size=10, mt_pattern="2H"),
    # ------------------------------------------------------------ C · zone 8  Kreg · guides   (metric portrait)
    H("C8-01", "Rip-Cut rail · hooks ×2", "Kreg", 8, MET, 2, "RIP-CUT", family="hook", hk_type="j", hk_w=30, hk_reach=50, hk_t=6, hk_tip=15, hk_ph=70, **JH),
    H("C8-02", "Pocket-hole jig", "Kreg", 8, MET, 1, "KREG JIG", family="tray", tr_type="bin", tr_w=142, tr_depth=72, tr_h=40, tr_front=22, tr_wall=2.4, tr_floor=3, tr_ph=50, mt_fix="jhook", mt_pattern="row"),
    H("C8-03", "Clamp triangle", "Kreg", 8, MET, 1, "TRIANGLE", family="hook", hk_type="j", hk_w=20, hk_reach=30, hk_t=6, hk_tip=10, hk_ph=70, **JH),
    H("C8-04", "Vernier caliper", "—", 8, MET, 1, "VERNIER", family="holster", hs_type="saddle", hs_inner_w=18, hs_inner_d=26, hs_arm=7, hs_h=30, hs_r=3, hs_flare=2, hs_ph=94, mt_fix="jhook", mt_pattern="grid", mt_cols=1, mt_rows=3),
    H("C8-05", "Rule 600 · strips ×2", "—", 8, MET, 2, "RULE 600", family="magstrip", mg_w=40, mg_h=120, mg_mode="embed", mg_n=1, mg_rows=3, mg_size="10x3", mg_cover=0.6, plate_t=6, mt_fix="jhook", mt_pattern="2V"),
    H("C8-06", "Rule 1000 aluminium · hooks ×2", "—", 8, MET, 2, "RULE 1000", family="hook", hk_type="j", hk_w=35, hk_reach=35, hk_t=6, hk_tip=12, hk_ph=70, **JH),
    # ------------------------------------------------------------ C · zone 9  rules · layout
    H("C9-01", "Dividers", "—", 9, MET, 1, "DIVIDERS", family="hook", hk_type="j", hk_w=16, hk_reach=30, hk_t=6, hk_tip=10, hk_ph=70, **JH),
    H("C9-02", "Rule 300", "—", 9, MET, 1, "RULE 300", family="magstrip", mg_w=40, mg_h=120, mg_mode="embed", mg_n=1, mg_rows=3, mg_size="10x3", mg_cover=0.6, plate_t=6, mt_fix="jhook", mt_pattern="2V"),
    H("C9-03", "Compass · scribe · awl", "—", 9, MET, 1, "LAYOUT", family="rack", rk_type="drivers", rk_n=3, rk_d=10, rk_pitch=22, rk_depth=28, rk_t=8, rk_margin=6, rk_ph=64, mt_fix="jhook", mt_pattern="auto"),
    H("C9-04", "Utility blade packs ×2", "Sky", 9, MET, 1, "BLADES", family="hook", hk_type="j", hk_w=25, hk_reach=30, hk_t=6, hk_tip=12, hk_ph=70, **JH),
    H("C9-05", "Scraper", "—", 9, MET, 1, "SCRAPER", family="hook", hk_type="j", hk_w=20, hk_reach=30, hk_t=6, hk_tip=10, hk_ph=70, **JH),
    # ------------------------------------------------------------ C · zone 10  tape · adhesive
    H("C10-01", "Masking tape rolls ×3", "—", 10, MET, 1, "TAPE", family="hook", hk_type="peg", hk_w=24, hk_reach=110, hk_t=12, hk_tip=8, hk_rib=12, hk_ph=70, **JH),
    H("C10-02", "Double-sided tape ×2", "—", 10, MET, 1, "DS TAPE", family="hook", hk_type="peg", hk_w=24, hk_reach=70, hk_t=12, hk_tip=8, hk_rib=10, hk_ph=70, **JH),
    H("C10-03", "Glue dots · sticker packs", "Bostik", 10, MET, 1, "GLUE", family="hook", hk_type="j", hk_w=20, hk_reach=30, hk_t=6, hk_tip=10, hk_ph=70, **JH),
    H("C10-04", "Brush 100", "—", 10, MET, 1, "BRUSH", family="hook", hk_type="j", hk_w=25, hk_reach=35, hk_t=6, hk_tip=12, hk_ph=70, **JH),
    H("C10-05", "Sanding block", "—", 10, MET, 1, "SANDING", family="tray", tr_type="tray", tr_w=78, tr_depth=36, tr_h=25, tr_wall=2.0, tr_floor=3, tr_ph=50, mt_fix="jhook", mt_pattern="2H"),
    H("C0-01", "Zone label plates ×5", "mdrn", 0, MET, 5, "ZONE", family="plate", pl_w=120, pl_h=28, plate_t=4, brand_size=10, mt_fix="jhook", mt_pattern="2H"),
    # ------------------------------------------------------------ C · zone 12  Gridfinity
    H("C12-01", "Gridfinity 2×1 shelf ×4", "—", 12, MET, 4, "GRID", family="gridfinity", gf_nx=2, gf_ny=1, gf_t=7, gf_tilt=10, gf_lip=4, gf_rim=2, gf_ph=44, mt_fix="jhook", mt_pattern="row"),
    # ------------------------------------------------------------ B · zone 13  long tools · saws · clamps  (metric landscape)
    H("B13-01", "F-clamps ×4", "—", 13, MET, 4, "CLAMP", family="hook", hk_type="j", hk_w=30, hk_reach=50, hk_t=7, hk_tip=20, hk_ph=70, **JH),
    H("B13-02", "Straightedge 1000 · hooks ×2", "—", 13, MET, 2, "STRAIGHT", family="hook", hk_type="j", hk_w=35, hk_reach=35, hk_t=6, hk_tip=12, hk_ph=70, **JH),
    H("B13-03", "Pull saw · hand saws ×2", "—", 13, MET, 2, "SAW", family="hook", hk_type="j", hk_w=30, hk_reach=40, hk_t=6, hk_tip=14, hk_ph=70, **JH),
    H("B13-04", "Extension cord (coiled)", "—", 13, MET, 1, "CORD", family="hook", hk_type="j", hk_w=45, hk_reach=60, hk_t=7, hk_tip=25, hk_rib=14, hk_ph=96, mt_fix="jhook", mt_pattern="grid", mt_cols=1, mt_rows=3),
    H("B0-01", "Zone label plates ×3", "mdrn", 0, MET, 3, "ZONE", family="plate", pl_w=150, pl_h=36, plate_t=4, brand_size=12, mt_fix="jhook", mt_pattern="2H"),
    # ------------------------------------------------------------ B · zone 14  Gridfinity shelf row
    H("B14-01", "Gridfinity 4×1 shelf ×7", "—", 14, MET, 7, "GRID", family="gridfinity", gf_nx=4, gf_ny=1, gf_t=8.5, gf_tilt=0, gf_lip=4, gf_rim=2, gf_magnets=True, gf_ph=44, mt_fix="jhook", mt_pattern="row"),
]
