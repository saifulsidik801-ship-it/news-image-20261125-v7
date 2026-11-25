#!/usr/bin/env python3
"""Render the front page for news-image-20261125 v7.

Design: a broadsheet front page, 1024x1024, 38 stories — every one first
reported Wednesday 25 November 2026. Three heroes with large drawn scenes,
13 numbered mids, a 22-item list, a filled map with numbered pins, a UTC
timeline strip, claim badges on EVERY story, and a DATE CHECK box.

Layout engine: a y-cursor. Every text block is wrapped and measured with
font ascent+descent BEFORE it is drawn; art and text live in separate
stacked boxes, so no text can ever sit under a picture. Art heights are
derived from the remaining page budget after all text is measured, so the
page ends flush at the bottom.

v7 vs v6: 50 stories -> 38 (the winning format of top-1/3/5); claim badges
everywhere; THE DAY IN UTC strip; WHY IT MATTERS on heroes; regions
rebalanced (max 8 per region); all 14 wrong-date v6 stories replaced with
verified Nov 25 stories; masthead subline carries only Nov 25 stories.
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
M = 10
CW = W - 2 * M
PAPER = (245, 241, 232)
NAVY = (27, 42, 74)
RED = (176, 30, 40)
INK = (17, 17, 17)
GREY = (85, 85, 85)
LINE = (153, 153, 153)
SEA = (214, 228, 235)
LAND = (216, 196, 158)
GOLD = (180, 150, 40)
GREEN = (46, 125, 50)
BLUE = (46, 90, 136)
TEAL = (0, 131, 143)
BROWN = (141, 110, 99)

FD = "/usr/share/fonts/truetype/dejavu"


def F(path, size):
    return ImageFont.truetype(os.path.join(FD, path), size)


F_MAST = F("DejaVuSerif-Bold.ttf", 48)
F_SUB = F("DejaVuSerif.ttf", 13)
F_NUM = F("DejaVuSans-Bold.ttf", 26)
F_NUMCAP = F("DejaVuSans.ttf", 10)
F_CONT = F("DejaVuSans-Bold.ttf", 10)
F_UTC_T = F("DejaVuSans-Bold.ttf", 10)
F_UTC = F("DejaVuSans.ttf", 10)
F_HERO_HEAD = F("DejaVuSerif-Bold.ttf", 19)
F_HERO_BODY = F("DejaVuSans.ttf", 11)
F_WIM = F("DejaVuSans.ttf", 10)
F_WIM_T = F("DejaVuSans-Bold.ttf", 10)
F_HERO_DATE = F("DejaVuSans-Bold.ttf", 10)
F_HERO_SRC = F("DejaVuSans.ttf", 9)
F_MID_HEAD = F("DejaVuSerif-Bold.ttf", 14)
F_MID_BODY = F("DejaVuSans.ttf", 10)
F_MID_DATE = F("DejaVuSans-Bold.ttf", 9)
F_MAP_T = F("DejaVuSans-Bold.ttf", 12)
F_LIST_H = F("DejaVuSans-Bold.ttf", 12)
F_LIST = F("DejaVuSans.ttf", 10)
F_LIST_N = F("DejaVuSans-Bold.ttf", 11)
F_DC_T = F("DejaVuSans-Bold.ttf", 11)
F_DC = F("DejaVuSans.ttf", 11)
F_FOOT = F("DejaVuSans.ttf", 9)


def wrap(text, font, max_w, d):
    """Greedy word wrap; returns the lines that fit max_w."""
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def lh(font):
    a, dd = font.getmetrics()
    return a + dd


def fit_lines(text, font, max_w, d, max_lines, min_size, fname):
    """Wrap to at most max_lines; shrink the font if needed (never below min)."""
    size = font.size
    while size >= min_size:
        f = F(fname, size)
        lines = wrap(text, f, max_w, d)
        if len(lines) <= max_lines:
            return lines, f
        size -= 1
    f = F(fname, min_size)
    return wrap(text, f, max_w, d)[:max_lines], f


def block_h(lines, font):
    return len(lines) * lh(font)


def put_lines(d, x, y, lines, font, fill):
    for ln in lines:
        d.text((x, y), ln, font=font, fill=fill)
        y += lh(font)
    return y


def num_badge(d, cx, cy, n, r=11):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED, outline=(255, 255, 255), width=1)
    f = F("DejaVuSans-Bold.ttf", 12 if n < 10 else 10)
    t = str(n)
    d.text((cx - d.textlength(t, font=f) / 2, cy - lh(f) / 2 + 1), t, font=f, fill=(255, 255, 255))


BADGE_STYLE = {
    "OFFICIAL": ((46, 90, 136), (255, 255, 255)),
    "REPORTED": ((255, 255, 255), (176, 30, 40)),
    "CLAIM": ((176, 30, 40), (255, 255, 255)),
    "CONFIRMED": ((46, 125, 50), (255, 255, 255)),
}


def claim_pill(d, x, y, label):
    """Small outlined/filled pill with the claim label; returns its width."""
    fill, fg = BADGE_STYLE[label]
    f = F("DejaVuSans-Bold.ttf", 8)
    tw = d.textlength(label, font=f)
    w = int(tw) + 10
    h = 13
    if fill == (255, 255, 255):
        d.rounded_rectangle([x, y, x + w, y + h], radius=3, fill=fill,
                            outline=(176, 30, 40), width=1)
    else:
        d.rounded_rectangle([x, y, x + w, y + h], radius=3, fill=fill)
    d.text((x + 5, y + 1), label, font=f, fill=fg)
    return w


# ------------------------------------------------------------------ data
NUMSTRIP = [
    ("−6.2%", "Asian chip stocks plunge"),
    ("20%", "top proposed US tariff"),
    ("47,000", "women killed by partner or kin"),
    ("+36%", "Bangladesh garment wage offer"),
    ("£2,166", "Ofgem price cap from January"),
    ("9", "dead, 17 trapped in Java pit"),
]

UTC_STRIP = [
    ("00:18", "Shenzhou lifts off"),
    ("01:31", "6 bodies found"),
    ("03:56", "Shenzhou docks"),
    ("~04:00", "Gaza strike"),
    ("04:28", "Zaporizhzhia out"),
    ("06:30", "Cartagena rescue"),
    ("15:00", "Iowa blast done"),
]

CONTINENTS = [("EUROPE", 8, BLUE), ("ASIA", 8, GOLD), ("N. AMERICA", 6, GREEN),
              ("MIDEAST", 4, RED), ("AFRICA", 3, BROWN), ("OCEANIA", 4, TEAL),
              ("LATIN AM", 2, (200, 120, 60)), ("WORLD", 3, GREY)]

HEROES = [
    dict(n=1, tag="TOP STORY", badge="OFFICIAL", date="WASHINGTON  •  TRADE",
         head="US proposes tariffs of up to 20% on EU, China and 12 more",
         body="USTR ends 8-month probe of 16 partners; China hit hardest at 20%. Duties from January at earliest.",
         wim="Two top trade partners face new duties.",
         src="(Reuters / AP)", scene="tariff"),
    dict(n=2, tag="MARKETS", badge="REPORTED", date="SEOUL  •  TOKYO  •  TAIPEI  •  MARKETS",
         head="AI doubts sink Asian chip stocks; Kospi closes −6.2%",
         body="Samsung −9.9%, SK Hynix −11.1%; Taiex −4.8%, Nikkei −2.8%. Worst AI day in months.",
         wim="Doubt over the AI spending boom.",
         src="(AP)", scene="crash"),
    dict(n=3, tag="SPACE", badge="OFFICIAL", date="JIUQUAN, CHINA  •  SPACE",
         head="Pakistan's first astronaut docks at China's space station",
         body="Muhammad Zeeshan Ali, 40, first foreigner on Tiangong; flew on Shenzhou-24, stays 5–10 days.",
         wim="First foreigner on China's station.",
         src="(Reuters / Xinhua)", scene="tiangong"),
]

MIDS = [
    dict(n=4, badge="CLAIM", date="STRAIT OF HORMUZ  •  GULF",
         head="Iran says mines set two tankers on fire in Hormuz",
         body="IRGC: two tankers struck mines and burned. Not independently verified.", scene="tanker"),
    dict(n=5, badge="REPORTED", date="WASHINGTON  •  SECURITY",
         head="Hackers breach CIA spy-agency system",
         body="NYT first reported; ARTEX AI tool suspected. No classified data exposed.", scene="server"),
    dict(n=6, badge="OFFICIAL", date="CANBERRA  •  DIPLOMACY",
         head="Solomon Islands signs security pact with Australia",
         body="A$740m over 10 years; Australia is primary security partner. No foreign bases.", scene="treaty"),
    dict(n=7, badge="REPORTED", date="DHAKA  •  LABOUR",
         head="Garment workers offered 36% pay rise",
         body="Wage board: Tk12,500 to Tk17,000 a month (wires reported 17,500).", scene="garment"),
    dict(n=8, badge="REPORTED", date="BOGOR, JAVA  •  DISASTER",
         head="9 dead, 17 still trapped in flooded gold pit",
         body="Rescuers pull bodies from a 100-metre unlicensed shaft in West Java.", scene="mine"),
    dict(n=9, badge="REPORTED", date="GAZA CITY  •  WAR",
         head="Strike kills Hamas security chief, family",
         body="Mohammad Abuelouf, wife and two daughters die in dawn strike on Shati camp.", scene="gaza"),
    dict(n=10, badge="OFFICIAL", date="SYDNEY  •  ECONOMY",
         head="Australia's inflation jumps to 4.9%",
         body="October CPI beats forecasts two weeks before the RBA meets; fuel +6.3%.", scene="cpi"),
    dict(n=11, badge="OFFICIAL", date="MIDDLETOWN, IOWA  •  ENVIRONMENT",
         head="US Army blows up lead azide stockpile",
         body="Two open-air blasts of ~5 tons despite fears of toxic dust on farms.", scene="bunker"),
    dict(n=12, badge="OFFICIAL", date="UNITED NATIONS  •  RIGHTS",
         head="UN: five women killed each hour by partner or kin",
         body="47,000 killed in 2025 — 60% of all femicides, 129 a day.", scene="unstats"),
    dict(n=13, badge="OFFICIAL", date="LONDON  •  ENERGY",
         head="UK energy price cap rises 26% in January",
         body="Ofgem: typical bill £1,723 to £2,166 a year from 1 January.", scene="bill"),
    dict(n=14, badge="OFFICIAL", date="BRUSSELS  •  EU",
         head="EU hosts six Western Balkan leaders",
         body="Summit on membership and the Growth Plan, on the eve of a budget summit.", scene="flags"),
    dict(n=15, badge="REPORTED", date="CARTAGENA  •  CRIME",
         head="Police free hostages in supermarket siege",
         body="All remaining ~20 freed in dawn rescue; one captor killed.", scene="store"),
    dict(n=16, badge="OFFICIAL", date="BRUSSELS  •  TECH",
         head="EU proposes €50bn fund for quantum tech",
         body="Quantum Act aims to make Europe a global leader by 2030.", scene="chip"),
]

LIST = [
    (17, "OFFICIAL", "Seoul: Bithumb breach: 19 data types"),
    (18, "REPORTED", "Karachi: building collapse: 3 dead"),
    (19, "REPORTED", "Paraná: storms: 6 dead, ~10,000 hit"),
    (20, "OFFICIAL", "Enugu: Pete Edochie dies, 79"),
    (21, "OFFICIAL", "London: Met still institutionally racist"),
    (22, "REPORTED", "Jerusalem: drop Netanyahu bribery charge"),
    (23, "OFFICIAL", "Cape Town: Ramaphosa wins Farmgate case"),
    (24, "REPORTED", "London: Eurostar strike cancels 8 trains"),
    (25, "REPORTED", "Khartoum: Sudan rejects Ethiopia offer"),
    (26, "OFFICIAL", "Pyongyang: N. Korea expels Swiss envoy"),
    (27, "OFFICIAL", "Kuala Lumpur: Malaysia orders 10 787s"),
    (28, "OFFICIAL", "Perth: Deloitte suspended over AI errors"),
    (29, "REPORTED", "Redmond: GPT-6.2 reaches Copilot"),
    (30, "OFFICIAL", "Vatican: Pope Leo laments COP31 collapse"),
    (31, "OFFICIAL", "Zaporizhzhia: NPP loses power, 17th time"),
    (32, "REPORTED", "Moscow: Kremlin dismisses 700k death toll"),
    (33, "OFFICIAL", "Auckland: a2 Milk A$62m deal approved"),
    (34, "REPORTED", "Sanaa: Houthis threaten Saudi ports"),
    (35, "REPORTED", "Warsaw: Poland may expel Russian envoy"),
    (36, "REPORTED", "Mississippi: plane: all 6 bodies found"),
    (37, "REPORTED", "Round Rock: Dell falls 10% on AI results"),
    (38, "REPORTED", "San Francisco: Anthropic slides below IPO"),
]

DATECHECK = ("Every story above was first reported on Wednesday 25 November 2026. Left out as "
             "earlier news: Dow 50,018.70 (Tue 24) · Huawei verdict (Tue 24) · Riyadh strike "
             "(Tue 24) · Chen probe (Tue 24) · Huang returns to Nvidia (Mon 23) · COP31 collapse "
             "(Sun 22) · Nepal quake (Tue 24) · El Chapo captured (20 Nov). Notes: CIA breach — "
             "NYT Tue 24, widely reported Wed 25 · UN femicide — UNODC Tue 24, UN Women Wed 25 · "
             "Bangladesh wage — board vote 17,000, wires 17,500 · Hormuz — UKMTO dates differ (22/23 Nov).")

LEGEND = ("OFFICIAL = government, agency or company statement  •  REPORTED = wire or outlet "
          "reporting  •  CLAIM = one side's word, unverified  •  CONFIRMED = two or more major outlets")


# ------------------------------------------------------------------ scenes
# Every scene fills its box edge-to-edge: background + midground + subject.
def _sky(d, x, y, w, h, top, bot):
    for i in range(h):
        t = i / max(1, h - 1)
        d.line([(x, y + i), (x + w, y + i)],
               fill=tuple(int(top[c] + (bot[c] - top[c]) * t) for c in range(3)))


def _stars(d, x, y, w, h, n=16, seed=11):
    r = random.Random(seed)
    for _ in range(n):
        sx, sy = x + r.randint(2, int(w) - 3), y + r.randint(2, int(h) // 2)
        s = r.choice([1, 1, 2])
        d.ellipse([sx, sy, sx + s, sy + s], fill=(255, 255, 220))


def scene_chip_tag(d, x, y, w, h, text):
    """Red tag chip inside a scene box: bottom-left on tall scenes (heroes),
    small top-left chip on short scenes (mids)."""
    if h <= 40:
        f = F("DejaVuSans-Bold.ttf", 8)
        tw = d.textlength(text, font=f)
        d.rectangle([x, y, x + tw + 10, y + 11], fill=RED)
        d.text((x + 5, y + 1), text, font=f, fill=(255, 255, 255))
        return
    f = F("DejaVuSans-Bold.ttf", 10)
    tw = d.textlength(text, font=f)
    d.rectangle([x, y + h - 15, x + tw + 12, y + h], fill=RED)
    d.text((x + 6, y + h - 14), text, font=f, fill=(255, 255, 255))


CHIPS = {"tariff": "UP TO 20%", "crash": "KOSPI −6.2%", "tiangong": "1ST FOREIGN VISITOR",
         "tanker": "2 TANKERS", "server": "HACK", "treaty": "TREATY SIGNED",
         "garment": "+36% PAY", "mine": "9 DEAD", "gaza": "4 KILLED", "cpi": "4.9%",
         "bunker": "10,000 LB", "unstats": "47,000", "bill": "+26%  £2,166",
         "flags": "EU + 6", "store": "RESCUE", "chip": "€50BN"}


def scene_tariff(d, x, y, w, h):
    _sky(d, x, y, w, h, (190, 215, 235), (235, 230, 210))
    d.rectangle([x, y + h * 0.66, x + w, y + h], fill=(40, 90, 140))
    d.polygon([(x + w * 0.04, y + h * 0.62), (x + w * 0.96, y + h * 0.62),
               (x + w * 0.88, y + h * 0.82), (x + w * 0.12, y + h * 0.82)], fill=(30, 30, 38))
    cols = [(200, 60, 50), (50, 120, 200), (220, 170, 40), (60, 160, 90), (200, 110, 40)]
    for r in range(2):
        for c in range(5):
            cx = x + w * (0.08 + 0.17 * c)
            cy = y + h * (0.34 + 0.14 * r)
            d.rectangle([cx, cy, cx + w * 0.15, cy + h * 0.12], fill=cols[(r + c) % 5],
                        outline=(255, 255, 255), width=1)
    d.line([(x + w * 0.86, y + h * 0.06), (x + w * 0.86, y + h * 0.62)], fill=(60, 60, 60), width=3)
    d.line([(x + w * 0.60, y + h * 0.08), (x + w * 0.98, y + h * 0.08)], fill=(60, 60, 60), width=3)
    # red circle stamp top-right: "20%"
    f = F("DejaVuSans-Bold.ttf", 13)
    sx, sy = x + w * 0.82, y + h * 0.16
    d.ellipse([sx - 15, sy - 13, sx + 15, sy + 13], fill=RED, outline=(255, 255, 255), width=1)
    d.text((sx - d.textlength("20%", font=f) / 2, sy - lh(f) / 2 + 1), "20%", font=f,
           fill=(255, 255, 255))
    scene_chip_tag(d, x, y, w, h, CHIPS["tariff"])


def scene_crash(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(16, 16, 24))
    for i in range(1, 5):
        d.line([(x, y + h * i / 5), (x + w, y + h * i / 5)], fill=(40, 40, 52), width=1)
    # falling red line
    pts = []
    vals = [0.22, 0.28, 0.26, 0.40, 0.36, 0.52, 0.48, 0.62, 0.58, 0.74, 0.70, 0.86]
    for i, v in enumerate(vals):
        pts.append((x + w * (0.04 + 0.92 * i / (len(vals) - 1)), y + h * v))
    d.line(pts, fill=(230, 60, 50), width=3)
    ex, ey = pts[-1]
    d.polygon([(ex, ey), (ex - 12, ey - 2), (ex - 4, ey + 10)], fill=(230, 60, 50))
    # chip bottom-left
    cx, cy, s = x + w * 0.16, y + h * 0.62, min(w, h) * 0.22
    d.rectangle([cx - s, cy - s, cx + s, cy + s], fill=(30, 120, 70), outline=(180, 220, 180), width=2)
    d.rectangle([cx - s * 0.5, cy - s * 0.5, cx + s * 0.5, cy + s * 0.5], fill=(60, 180, 110))
    for k in (-1, 0, 1):
        d.line([(cx + k * s * 0.55, cy - s * 1.1), (cx + k * s * 0.55, cy - s)], fill=(200, 200, 200), width=2)
        d.line([(cx - s * 1.1, cy + k * s * 0.55), (cx - s, cy + k * s * 0.55)], fill=(200, 200, 200), width=2)
    f = F("DejaVuSans-Bold.ttf", 11)
    d.text((x + w * 0.62, y + h * 0.10), "KOSPI", font=f, fill=(255, 255, 255))
    d.text((x + w * 0.62, y + h * 0.10 + lh(f)), "−6.2%", font=F("DejaVuSans-Bold.ttf", 15), fill=(230, 60, 50))
    d.text((x + w * 0.62, y + h * 0.10 + lh(f) + 18), "SK HYNIX −11.1%", font=f, fill=(200, 200, 200))
    scene_chip_tag(d, x, y, w, h, CHIPS["crash"])


def scene_tiangong(d, x, y, w, h):
    _sky(d, x, y, w, h, (8, 12, 32), (30, 44, 80))
    _stars(d, x, y, w, h, n=22, seed=5)
    # station: central module + solar wings
    cx, cy = x + w * 0.58, y + h * 0.42
    d.rectangle([cx - w * 0.10, cy - h * 0.10, cx + w * 0.10, cy + h * 0.10], fill=(220, 220, 225))
    d.rectangle([cx - w * 0.10, cy - h * 0.06, cx + w * 0.10, cy + h * 0.06], fill=(180, 180, 190))
    for sx in (-1, 1):
        wx0 = cx + sx * w * 0.12
        wx1 = cx + sx * w * 0.34
        d.rectangle([min(wx0, wx1), cy - h * 0.16, max(wx0, wx1), cy + h * 0.16],
                    fill=(40, 80, 180), outline=(120, 160, 220), width=1)
        for k in range(3):
            gx = min(wx0, wx1) + (wx1 - wx0) * k / 3 if sx > 0 else min(wx0, wx1) + (wx1 - wx0) * k / 3
            d.line([(gx, cy - h * 0.16), (gx, cy + h * 0.16)], fill=(120, 160, 220), width=1)
    # rocket below-left
    rx, rw = x + w * 0.10, w * 0.09
    d.rectangle([rx, y + h * 0.30, rx + rw, y + h * 0.72], fill=(240, 240, 240))
    d.polygon([(rx, y + h * 0.30), (rx + rw / 2, y + h * 0.18), (rx + rw, y + h * 0.30)],
              fill=(176, 30, 40))
    d.polygon([(rx + rw * 0.25, y + h * 0.72), (rx + rw * 0.5, y + h * 0.80),
               (rx + rw * 0.75, y + h * 0.72)], fill=(255, 170, 40))
    # flags
    d.rectangle([x + w * 0.80, y + h * 0.08, x + w * 0.86, y + h * 0.20], fill=(0, 120, 60))
    d.rectangle([x + w * 0.80, y + h * 0.08, x + w * 0.86, y + h * 0.20], outline=(255, 255, 255), width=1)
    d.rectangle([x + w * 0.87, y + h * 0.08, x + w * 0.93, y + h * 0.20], fill=(220, 40, 40))
    scene_chip_tag(d, x, y, w, h, CHIPS["tiangong"])


def scene_tanker(d, x, y, w, h):
    _sky(d, x, y, w, h, (230, 140, 70), (200, 90, 40))
    d.rectangle([x, y + h * 0.62, x + w, y + h], fill=(30, 60, 100))
    # tanker hull
    d.polygon([(x + w * 0.08, y + h * 0.55), (x + w * 0.92, y + h * 0.55),
               (x + w * 0.86, y + h * 0.72), (x + w * 0.14, y + h * 0.72)], fill=(40, 40, 48))
    d.rectangle([x + w * 0.62, y + h * 0.38, x + w * 0.78, y + h * 0.55], fill=(220, 220, 220))
    # flames + smoke
    for fx, fh in [(0.30, 0.30), (0.45, 0.38), (0.60, 0.26)]:
        d.polygon([(x + w * fx - 6, y + h * 0.55), (x + w * fx, y + h * (0.55 - fh)),
                   (x + w * fx + 6, y + h * 0.55)], fill=(255, 170, 40))
        d.polygon([(x + w * fx - 3, y + h * 0.55), (x + w * fx, y + h * (0.55 - fh * 0.6)),
                   (x + w * fx + 3, y + h * 0.55)], fill=(255, 220, 80))
    for cx, cy, r in [(0.35, 0.20, 0.07), (0.48, 0.14, 0.09), (0.62, 0.22, 0.06)]:
        d.ellipse([x + w * (cx - r), y + h * (cy - r * 0.7), x + w * (cx + r), y + h * (cy + r * 0.7)],
                  fill=(60, 60, 60))
    scene_chip_tag(d, x, y, w, h, CHIPS["tanker"])


def scene_server(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(18, 28, 52))
    for rx in (x + w * 0.02, x + w * 0.72):
        d.rectangle([rx, y + h * 0.06, rx + w * 0.26, y + h * 0.94], fill=(38, 52, 82))
        for r in range(6):
            yy = y + h * (0.12 + 0.13 * r)
            d.rectangle([rx + 3, yy, rx + w * 0.26 - 3, yy + h * 0.07], fill=(24, 36, 64))
            for c in range(4):
                cc = (60, 220, 90) if (r + c) % 3 else (255, 200, 60)
                d.ellipse([rx + 5 + c * w * 0.055, yy + 2, rx + 9 + c * w * 0.055, yy + 6], fill=cc)
    cx, cy = x + w * 0.50, y + h * 0.48
    s = h * 0.36
    d.polygon([(cx, cy - s), (cx + s * 0.75, cy - s * 0.6), (cx + s * 0.75, cy + s * 0.1),
               (cx, cy + s * 0.75), (cx - s * 0.75, cy + s * 0.1), (cx - s * 0.75, cy - s * 0.6)],
              fill=(230, 180, 40), outline=(150, 110, 20), width=2)
    d.line([(cx - s * 0.15, cy - s * 0.45), (cx + s * 0.1, cy - s * 0.05),
            (cx + s * 0.35, cy + s * 0.45), (cx - s * 0.1, cy + s * 0.05)],
           fill=(120, 30, 30), width=3)
    scene_chip_tag(d, x, y, w, h, CHIPS["server"])


def scene_treaty(d, x, y, w, h):
    _sky(d, x, y, w, h, (200, 220, 235), (240, 235, 220))
    d.rectangle([x, y + h * 0.72, x + w, y + h], fill=(120, 140, 110))
    # two flags
    fcols = [(0, 120, 60), (0, 40, 120)]
    for i in range(2):
        px = x + w * (0.18 + 0.30 * i)
        d.line([(px, y + h * 0.14), (px, y + h * 0.70)], fill=(70, 70, 70), width=2)
        d.polygon([(px, y + h * 0.14), (px + w * 0.16, y + h * 0.20), (px, y + h * 0.26)],
                  fill=fcols[i])
    # document on a table
    d.rectangle([x + w * 0.55, y + h * 0.42, x + w * 0.92, y + h * 0.72], fill=(120, 90, 50))
    d.rectangle([x + w * 0.58, y + h * 0.34, x + w * 0.89, y + h * 0.46], fill=(255, 255, 255))
    for k in range(2):
        d.line([(x + w * 0.61, y + h * (0.38 + 0.03 * k)), (x + w * 0.86, y + h * (0.38 + 0.03 * k))],
               fill=(120, 120, 120), width=1)
    # handshake dots
    d.ellipse([x + w * 0.44, y + h * 0.52, x + w * 0.52, y + h * 0.62], fill=(240, 200, 160))
    scene_chip_tag(d, x, y, w, h, CHIPS["treaty"])


def scene_garment(d, x, y, w, h):
    _sky(d, x, y, w, h, (210, 225, 240), (240, 238, 228))
    d.rectangle([x, y + h * 0.70, x + w, y + h], fill=(150, 150, 145))
    # factory
    d.rectangle([x + w * 0.08, y + h * 0.40, x + w * 0.92, y + h * 0.72], fill=(200, 190, 170))
    d.polygon([(x + w * 0.08, y + h * 0.42), (x + w * 0.30, y + h * 0.16),
               (x + w * 0.52, y + h * 0.42)], fill=(120, 120, 120))
    for i in range(3):
        d.rectangle([x + w * (0.16 + 0.22 * i), y + h * 0.50, x + w * (0.28 + 0.22 * i), y + h * 0.66],
                    fill=(120, 170, 200))
    # shirts on a line
    d.line([(x + w * 0.06, y + h * 0.24), (x + w * 0.94, y + h * 0.24)], fill=(80, 80, 80), width=1)
    for i, col in enumerate([(200, 60, 50), (50, 120, 200), (220, 170, 40)]):
        sx = x + w * (0.14 + 0.28 * i)
        d.polygon([(sx, y + h * 0.24), (sx + w * 0.12, y + h * 0.24), (sx + w * 0.12, y + h * 0.42),
                   (sx + w * 0.08, y + h * 0.42), (sx + w * 0.06, y + h * 0.34),
                   (sx + w * 0.04, y + h * 0.42), (sx, y + h * 0.42)], fill=col)
    scene_chip_tag(d, x, y, w, h, CHIPS["garment"])


def scene_mine(d, x, y, w, h):
    _sky(d, x, y, w, h, (170, 195, 215), (225, 225, 215))
    d.rectangle([x, y + h * 0.72, x + w, y + h], fill=(110, 100, 80))
    # headframe
    d.polygon([(x + w * 0.30, y + h * 0.72), (x + w * 0.42, y + h * 0.14),
               (x + w * 0.50, y + h * 0.14), (x + w * 0.62, y + h * 0.72)], fill=(60, 60, 66))
    d.line([(x + w * 0.46, y + h * 0.14), (x + w * 0.46, y + h * 0.72)], fill=(200, 200, 200), width=2)
    # shaft opening
    d.ellipse([x + w * 0.36, y + h * 0.66, x + w * 0.56, y + h * 0.80], fill=(20, 20, 20))
    # water + helmet
    d.rectangle([x + w * 0.68, y + h * 0.60, x + w * 0.94, y + h * 0.72], fill=(60, 120, 180))
    d.ellipse([x + w * 0.76, y + h * 0.52, x + w * 0.88, y + h * 0.62], fill=(240, 200, 20))
    d.rectangle([x + w * 0.81, y + h * 0.50, x + w * 0.83, y + h * 0.54], fill=(240, 200, 20))
    scene_chip_tag(d, x, y, w, h, CHIPS["mine"])


def scene_gaza(d, x, y, w, h):
    _sky(d, x, y, w, h, (70, 60, 80), (220, 140, 80))
    d.rectangle([x, y + h * 0.74, x + w, y + h], fill=(60, 55, 50))
    # apartment block
    d.rectangle([x + w * 0.14, y + h * 0.26, x + w * 0.86, y + h * 0.76], fill=(200, 190, 170))
    for r in range(3):
        for c in range(4):
            wx = x + w * (0.20 + 0.16 * c)
            wy = y + h * (0.32 + 0.13 * r)
            col = (40, 40, 40) if (r, c) != (1, 2) else (255, 200, 90)
            d.rectangle([wx, wy, wx + w * 0.08, wy + h * 0.07], fill=col)
    # smoke + fire glow
    for cx, cy, r in [(0.70, 0.18, 0.08), (0.78, 0.12, 0.10), (0.62, 0.10, 0.06)]:
        d.ellipse([x + w * (cx - r), y + h * (cy - r * 0.7), x + w * (cx + r), y + h * (cy + r * 0.7)],
                  fill=(70, 70, 70))
    d.ellipse([x + w * 0.66, y + h * 0.60, x + w * 0.80, y + h * 0.74], fill=(255, 170, 40))
    scene_chip_tag(d, x, y, w, h, CHIPS["gaza"])


def scene_cpi(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(245, 244, 238))
    for i in range(1, 5):
        d.line([(x, y + h * i / 5), (x + w, y + h * i / 5)], fill=(220, 220, 210), width=1)
    vals = [("3.6", 0.72), ("3.8", 0.66), ("4.1", 0.60), ("4.3", 0.52), ("4.9", 0.38)]
    bw = w / 5
    for i, (lab, v) in enumerate(vals):
        bx = x + bw * i + bw * 0.18
        col = RED if i == 4 else (46, 90, 136)
        d.rectangle([bx, y + h * v, bx + bw * 0.64, y + h * 0.92], fill=col)
        f = F("DejaVuSans-Bold.ttf", 9)
        lx = bx + bw * 0.32 - d.textlength(lab, font=f) / 2
        # label above the bar if it fits inside the scene, else inside the bar
        if y + h * v - 12 >= y + 1:
            d.text((lx, y + h * v - 12), lab, font=f, fill=INK)
        else:
            d.text((lx, y + h * v + 1), lab, font=f, fill=(255, 255, 255))


def scene_bunker(d, x, y, w, h):
    _sky(d, x, y, w, h, (180, 200, 210), (220, 215, 195))
    d.rectangle([x, y + h * 0.70, x + w, y + h], fill=(110, 130, 90))
    d.pieslice([x + w * 0.14, y + h * 0.34, x + w * 0.66, y + h * 0.94], 180, 360, fill=(80, 85, 80))
    d.rectangle([x + w * 0.14, y + h * 0.64, x + w * 0.66, y + h * 0.74], fill=(60, 64, 60))
    d.rectangle([x + w * 0.36, y + h * 0.66, x + w * 0.44, y + h * 0.76], fill=(30, 30, 30))
    bx, by = x + w * 0.82, y + h * 0.34
    for ang in range(0, 360, 30):
        a = math.radians(ang)
        d.line([(bx, by), (bx + 18 * math.cos(a), by + 13 * math.sin(a))], fill=(255, 170, 40), width=3)
    d.ellipse([bx - 9, by - 7, bx + 9, by + 7], fill=(255, 220, 80))
    scene_chip_tag(d, x, y, w, h, CHIPS["bunker"])


def scene_unstats(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(245, 244, 238))
    for i in range(1, 5):
        d.line([(x, y + h * i / 5), (x + w, y + h * i / 5)], fill=(220, 220, 210), width=1)
    # regional bars: Africa 8.4, Oceania 3.1, Asia 1.1, Europe 0.8, Americas 0.7 (per 100k)
    # (no tag chip here: the row labels start at the top-left corner)
    vals = [("AFRICA", 8.4, 0.30), ("OCEANIA", 3.1, 0.55), ("ASIA", 1.1, 0.70),
            ("EUROPE", 0.8, 0.78), ("AMERICAS", 0.7, 0.82)]
    f = F("DejaVuSans-Bold.ttf", 8)
    for i, (lab, v, top) in enumerate(vals):
        yy = y + h * (0.10 + 0.16 * i)
        d.text((x + 4, yy), lab, font=f, fill=INK)
        bw = w * 0.55 * (v / 8.4)
        d.rectangle([x + w * 0.32, yy, x + w * 0.32 + bw, yy + h * 0.10],
                    fill=RED if i == 0 else (46, 90, 136))


def scene_bill(d, x, y, w, h):
    _sky(d, x, y, w, h, (200, 215, 235), (240, 235, 220))
    d.rectangle([x, y + h * 0.72, x + w, y + h], fill=(140, 130, 110))
    # house
    d.rectangle([x + w * 0.10, y + h * 0.40, x + w * 0.55, y + h * 0.74], fill=(235, 225, 205))
    d.polygon([(x + w * 0.05, y + h * 0.42), (x + w * 0.325, y + h * 0.20),
               (x + w * 0.60, y + h * 0.42)], fill=(176, 30, 40))
    d.rectangle([x + w * 0.28, y + h * 0.56, x + w * 0.38, y + h * 0.74], fill=(90, 60, 40))
    # bill
    d.rectangle([x + w * 0.62, y + h * 0.22, x + w * 0.92, y + h * 0.72], fill=(255, 255, 255),
                outline=(120, 120, 120), width=1)
    for k in range(3):
        d.line([(x + w * 0.66, y + h * (0.30 + 0.08 * k)), (x + w * 0.88, y + h * (0.30 + 0.08 * k))],
               fill=(150, 150, 150), width=1)
    d.polygon([(x + w * 0.80, y + h * 0.52), (x + w * 0.74, y + h * 0.62), (x + w * 0.78, y + h * 0.62),
               (x + w * 0.72, y + h * 0.72), (x + w * 0.82, y + h * 0.60), (x + w * 0.78, y + h * 0.60)],
              fill=(255, 200, 20))
    scene_chip_tag(d, x, y, w, h, CHIPS["bill"])


def scene_flags(d, x, y, w, h):
    _sky(d, x, y, w, h, (185, 210, 235), (240, 235, 220))
    d.rectangle([x, y + h * 0.72, x + w, y + h], fill=(140, 130, 110))
    fcols = [(200, 60, 50), (50, 110, 200), (240, 200, 40), (60, 160, 90), (150, 80, 180)]
    for i in range(5):
        px = x + w * (0.10 + 0.18 * i)
        d.line([(px, y + h * 0.16), (px, y + h * 0.72)], fill=(70, 70, 70), width=2)
        d.polygon([(px, y + h * 0.16), (px + w * 0.13, y + h * 0.22), (px, y + h * 0.28)],
                  fill=fcols[i])
    d.rectangle([x + w * 0.36, y + h * 0.56, x + w * 0.64, y + h * 0.74], fill=(60, 55, 70))
    d.rectangle([x + w * 0.42, y + h * 0.50, x + w * 0.58, y + h * 0.56], fill=(90, 85, 100))
    d.ellipse([x + w * 0.46, y + h * 0.38, x + w * 0.54, y + h * 0.50], fill=(240, 200, 160))
    scene_chip_tag(d, x, y, w, h, CHIPS["flags"])


def scene_store(d, x, y, w, h):
    _sky(d, x, y, w, h, (210, 225, 240), (240, 238, 228))
    d.rectangle([x, y + h * 0.70, x + w, y + h], fill=(150, 150, 145))
    d.rectangle([x + w * 0.06, y + h * 0.30, x + w * 0.94, y + h * 0.72], fill=(225, 215, 195))
    for i in range(6):
        col = (200, 60, 50) if i % 2 == 0 else (240, 240, 235)
        d.polygon([(x + w * (0.06 + 0.146 * i), y + h * 0.30), (x + w * (0.20 + 0.146 * i), y + h * 0.30),
                   (x + w * (0.17 + 0.146 * i), y + h * 0.44), (x + w * (0.09 + 0.146 * i), y + h * 0.44)],
                  fill=col)
    d.rectangle([x + w * 0.14, y + h * 0.48, x + w * 0.42, y + h * 0.70], fill=(120, 170, 200))
    d.rectangle([x + w * 0.58, y + h * 0.48, x + w * 0.86, y + h * 0.70], fill=(120, 170, 200))
    for yy in (0.74, 0.84):
        d.rectangle([x, y + h * yy, x + w, y + h * (yy + 0.07)], fill=(240, 200, 20))
        for i in range(10):
            xx = x + w * i / 10
            d.polygon([(xx, y + h * (yy + 0.07)), (xx + w * 0.05, y + h * (yy + 0.07)),
                       (xx + w * 0.10, y + h * yy), (xx + w * 0.05, y + h * yy)], fill=(20, 20, 20))
    scene_chip_tag(d, x, y, w, h, CHIPS["store"])


def scene_chip(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(28, 44, 66))
    for i in range(5):
        d.line([(x, y + h * i / 5), (x + w, y + h * i / 5)], fill=(44, 66, 96), width=1)
    cx, cy, s = x + w * 0.5, y + h * 0.52, min(w, h) * 0.30
    d.rectangle([cx - s, cy - s, cx + s, cy + s], fill=(30, 120, 70), outline=(180, 220, 180), width=2)
    d.rectangle([cx - s * 0.55, cy - s * 0.55, cx + s * 0.55, cy + s * 0.55], fill=(60, 180, 110))
    for k in range(-1, 2):
        d.line([(cx + k * s * 0.6, cy - s * 1.15), (cx + k * s * 0.6, cy - s)], fill=(200, 200, 200), width=2)
        d.line([(cx + k * s * 0.6, cy + s), (cx + k * s * 0.6, cy + s * 1.15)], fill=(200, 200, 200), width=2)
        d.line([(cx - s * 1.15, cy + k * s * 0.6), (cx - s, cy + k * s * 0.6)], fill=(200, 200, 200), width=2)
        d.line([(cx + s, cy + k * s * 0.6), (cx + s * 1.15, cy + k * s * 0.6)], fill=(200, 200, 200), width=2)
    # atom rings for quantum
    for r in (0.42, 0.30):
        d.ellipse([cx - s * r * 2.2, cy - s * r, cx + s * r * 2.2, cy + s * r], outline=(120, 200, 255), width=1)
    scene_chip_tag(d, x, y, w, h, CHIPS["chip"])


SCENES = {"tariff": scene_tariff, "crash": scene_crash, "tiangong": scene_tiangong,
          "tanker": scene_tanker, "server": scene_server, "treaty": scene_treaty,
          "garment": scene_garment, "mine": scene_mine, "gaza": scene_gaza,
          "cpi": scene_cpi, "bunker": scene_bunker, "unstats": scene_unstats,
          "bill": scene_bill, "flags": scene_flags, "store": scene_store, "chip": scene_chip}


# ------------------------------------------------------------------ map + glyphs
LAND_POLYS = [
    [(30, 20), (150, 8), (260, 18), (300, 45), (250, 70), (180, 75), (120, 60), (40, 45)],
    [(330, 5), (360, 5), (360, 22), (335, 22)],
    [(270, 85), (320, 80), (350, 105), (330, 150), (295, 165), (270, 130)],
    [(470, 15), (530, 10), (555, 28), (520, 48), (480, 45), (460, 30)],
    [(470, 55), (540, 50), (560, 80), (530, 130), (490, 135), (465, 95)],
    [(560, 12), (760, 8), (900, 25), (950, 55), (880, 75), (760, 70), (640, 55), (565, 40)],
    [(800, 125), (880, 120), (900, 140), (850, 155), (800, 145)],
]
# pins for stories 1-16 (map space 1000x180)
PINS = {1: (165, 55), 2: (855, 38), 3: (800, 30), 4: (590, 62), 5: (190, 42),
        6: (880, 128), 7: (760, 55), 8: (820, 95), 9: (545, 45), 10: (915, 142),
        11: (140, 42), 12: (205, 48), 13: (472, 30), 14: (490, 32), 15: (240, 95),
        16: (520, 46)}


def draw_map(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=SEA)
    for i in range(1, 7):
        d.line([(x, y + h * i / 7), (x + w, y + h * i / 7)], fill=(190, 205, 215), width=1)
    for i in range(1, 10):
        d.line([(x + w * i / 10, y), (x + w * i / 10, y + h)], fill=(190, 205, 215), width=1)
    sx, sy = w / 1000.0, h / 180.0
    for poly in LAND_POLYS:
        d.polygon([(x + px * sx, y + py * sy) for px, py in poly], fill=LAND,
                  outline=(180, 160, 120))
    for gx, gy, gw, gh in [(775, 92, 14, 8), (805, 100, 18, 9), (838, 90, 12, 7)]:
        d.ellipse([x + gx * sx, y + gy * sy, x + (gx + gw) * sx, y + (gy + gh) * sy], fill=LAND)
    for n, (px, py) in PINS.items():
        cx, cy = x + px * sx, y + py * sy
        r = 8
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED, outline=(255, 255, 255), width=1)
        f = F("DejaVuSans-Bold.ttf", 9 if n < 10 else 8)
        t = str(n)
        d.text((cx - d.textlength(t, font=f) / 2, cy - lh(f) / 2 + 1), t, font=f,
               fill=(255, 255, 255))


GLYPHS = ["flag", "bars", "chip", "ball", "cross", "cloud", "star", "bolt"]
GLYPH_COLS = [BLUE, RED, GREEN, GOLD, TEAL, BROWN]


def draw_glyph(d, x, y, s, kind, col):
    d.rounded_rectangle([x, y, x + s, y + s], radius=2, fill=col)
    c = (255, 255, 255)
    if kind == "flag":
        d.polygon([(x + 2, y + 2), (x + s - 2, y + 4), (x + 2, y + 6)], fill=c)
        d.line([(x + 2, y + 2), (x + 2, y + s - 2)], fill=c, width=1)
    elif kind == "bars":
        for i, bh in enumerate((4, 7, 5)):
            d.rectangle([x + 2 + i * 3, y + s - 2 - bh, x + 4 + i * 3, y + s - 2], fill=c)
    elif kind == "chip":
        d.rectangle([x + 3, y + 3, x + s - 3, y + s - 3], outline=c, width=1)
        d.rectangle([x + 4, y + 4, x + s - 4, y + s - 4], fill=c)
    elif kind == "ball":
        d.ellipse([x + 2, y + 2, x + s - 2, y + s - 2], outline=c, width=1)
    elif kind == "cross":
        d.rectangle([x + s // 2 - 1, y + 2, x + s // 2 + 1, y + s - 2], fill=c)
        d.rectangle([x + 2, y + s // 2 - 1, x + s - 2, y + s // 2 + 1], fill=c)
    elif kind == "cloud":
        d.ellipse([x + 2, y + 4, x + s - 4, y + s - 3], fill=c)
    elif kind == "star":
        cx, cy = x + s / 2, y + s / 2
        pts = []
        for k in range(10):
            r = s / 2 - 1 if k % 2 == 0 else s / 4
            a = math.radians(-90 + 36 * k)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        d.polygon(pts, fill=c)
    else:  # bolt
        d.polygon([(x + s * 0.6, y + 1), (x + s * 0.3, y + s * 0.55), (x + s * 0.5, y + s * 0.55),
                   (x + s * 0.4, y + s - 1), (x + s * 0.7, y + s * 0.45), (x + s * 0.5, y + s * 0.45)],
                  fill=c)


# ------------------------------------------------------------------ layout
def pill_w(d, label):
    f = F("DejaVuSans-Bold.ttf", 8)
    return int(d.textlength(label, font=f)) + 10


def fit_text(text, font, max_w, d):
    """Shorten text with an ellipsis so it fits max_w."""
    while d.textlength(text, font=font) > max_w and " " in text:
        text = text.rsplit(" ", 1)[0] + "…"
    return text


def measure_hero(d, card, w):
    tw = w - 10
    head_lines, head_f = fit_lines(card["head"], F_HERO_HEAD, tw, d, 2, 16, "DejaVuSerif-Bold.ttf")
    body_lines = wrap(card["body"], F_HERO_BODY, tw, d)[:2]
    # WHY IT MATTERS: label takes its own width; text wraps in the rest (max 2 lines)
    label_w = d.textlength("WHY IT MATTERS  ", font=F_WIM_T)
    wim_lines = wrap(card["wim"], F_WIM, tw - label_w, d)[:2]
    h = (lh(F_HERO_DATE) + block_h(head_lines, head_f) + block_h(body_lines, F_HERO_BODY)
         + block_h(wim_lines, F_WIM) + lh(F_HERO_SRC) + 8)
    return h, head_lines, head_f, body_lines, wim_lines, label_w


def measure_mid(d, card, w):
    tw = w - 10
    head_lines, head_f = fit_lines(card["head"], F_MID_HEAD, tw, d, 2, 12, "DejaVuSerif-Bold.ttf")
    body_lines = wrap(card["body"], F_MID_BODY, tw, d)[:2]
    h = lh(F_MID_DATE) + block_h(head_lines, head_f) + block_h(body_lines, F_MID_BODY) + 6
    return h, head_lines, head_f, body_lines


def render():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    y = 0

    # --- top strip
    d.rectangle([0, 0, W, 18], fill=NAVY)
    d.text((M, 2), "THE WORLD IN ONE DAY", font=F("DejaVuSans-Bold.ttf", 11), fill=(255, 255, 255))
    rt = "38 STORIES  •  8 REGIONS  •  EVERY ONE FIRST REPORTED WEDNESDAY 25 NOVEMBER 2026"
    d.text((W - M - d.textlength(rt, font=F("DejaVuSans-Bold.ttf", 11)), 2), rt,
           font=F("DejaVuSans-Bold.ttf", 11), fill=(255, 255, 255))
    y = 18

    # --- masthead
    mt = "Wednesday 25 November 2026"
    d.text(((W - d.textlength(mt, font=F_MAST)) / 2, y), mt, font=F_MAST, fill=INK)
    y += lh(F_MAST) - 2
    sub = "US tariffs up to 20% on 14 partners  •  Asian chip stocks crash, Kospi −6.2%  •  Pakistan's first astronaut docks at Tiangong"
    d.text(((W - d.textlength(sub, font=F_SUB)) / 2, y), sub, font=F_SUB, fill=RED)
    y += lh(F_SUB) + 4

    # --- number strip
    cell_w = CW / 6
    for i, (num, cap) in enumerate(NUMSTRIP):
        cx = M + cell_w * i
        d.text((cx + (cell_w - d.textlength(num, font=F_NUM)) / 2, y), num, font=F_NUM, fill=INK)
        cap_lines = wrap(cap, F_NUMCAP, cell_w - 6, d)[:1]
        for cl in cap_lines:
            d.text((cx + (cell_w - d.textlength(cl, font=F_NUMCAP)) / 2, y + lh(F_NUM) + 1),
                   cl, font=F_NUMCAP, fill=GREY)
        if i:
            d.line([(cx, y + 2), (cx, y + lh(F_NUM) + lh(F_NUMCAP))], fill=LINE, width=1)
    y += lh(F_NUM) + lh(F_NUMCAP) + 6

    # --- continent bar
    bx = M
    for name, cnt, col in CONTINENTS:
        d.rectangle([bx, y + 1, bx + 10, y + 11], fill=col)
        t = f"{name} {cnt}"
        d.text((bx + 13, y), t, font=F_CONT, fill=INK)
        bx += 13 + d.textlength(t, font=F_CONT) + 16
    y += lh(F_CONT) + 4

    # --- UTC strip (navy band, measured height: label + wrapped items)
    utc_items = "  •  ".join(f"{t} {s}" for t, s in UTC_STRIP)
    utc_lines = wrap(utc_items, F_UTC, CW - 118, d)
    utc_h = max(lh(F_UTC), block_h(utc_lines, F_UTC)) + 8
    d.rectangle([M, y, W - M, y + utc_h], fill=NAVY)
    d.text((M + 6, y + 4), "THE DAY IN UTC", font=F_UTC_T, fill=(240, 200, 60))
    put_lines(d, M + 118, y + 4, utc_lines, F_UTC, (255, 255, 255))
    y += utc_h + 4

    # --- measure all story text (heroes + mids)
    hero_w = (CW - 2 * 6) / 3
    mid_w = (CW - 4 * 4) / 5
    wide_w = (CW - 2 * 4) / 3
    hero_m = [measure_hero(d, c, hero_w) for c in HEROES]
    mid_m = []
    for i, c in enumerate(MIDS):
        w = wide_w if i >= 10 else mid_w
        mid_m.append(measure_mid(d, c, w))
    hero_text = max(m[0] for m in hero_m)
    mid_text = [max(mid_m[r * 5 + k][0] for k in range(5)) + 6 for r in range(2)]
    mid_text.append(max(mid_m[10 + k][0] for k in range(3)) + 6)
    dc_lines = wrap(DATECHECK, F_DC, CW - 16, d)
    dc_h = lh(F_DC_T) + block_h(dc_lines, F_DC) + 8
    list_row_h = lh(F_LIST)
    list_h = lh(F_LIST_H) + 2 + 8 * list_row_h

    # --- fit pass: art heights fill the remaining budget exactly
    # gaps between sections: heroes +3, mid rows +3 x3, map +3, list +3, DATE CHECK +2 = 20
    fixed = (y + hero_text + sum(mid_text) + (lh(F_MAP_T) + lh(F_CONT) + 4)
             + list_h + dc_h + 2 * lh(F_FOOT) + 20)
    avail = H - fixed
    hero_art, mid_art, map_art = 90, 32, 50
    art_total = hero_art + 3 * mid_art + map_art
    scale = avail / art_total
    hero_art = max(56, int(hero_art * scale))
    mid_art = max(24, int(mid_art * scale))
    map_art = max(40, int(map_art * scale))
    # exact flush: give the truncation remainder to the map (most flexible)
    rem = avail - (hero_art + 3 * mid_art + map_art)
    if rem >= 0:
        map_art += rem
    else:
        hero_art += rem
    print(f"fit: avail={avail} scale={scale:.3f} hero_art={hero_art} mid_art={mid_art} "
          f"map_art={map_art} hero_text={hero_text} mid_text={mid_text} dc_h={dc_h} "
          f"utc_h={utc_h} list_h={list_h}")

    # --- heroes
    for i, c in enumerate(HEROES):
        x = M + i * (hero_w + 6)
        d.rectangle([x, y, x + hero_w, y + hero_art + hero_text], outline=LINE, width=1)
        SCENES[c["scene"]](d, x + 1, y + 1, hero_w - 2, hero_art - 1)
        d.rectangle([x + 1, y + 1, x + 86, y + 17], fill=RED)
        d.text((x + 6, y + 2), c["tag"], font=F("DejaVuSans-Bold.ttf", 9), fill=(255, 255, 255))
        num_badge(d, x + hero_w - 14, y + 14, c["n"])
        ty = y + hero_art + 3
        pw = pill_w(d, c["badge"])
        claim_pill(d, x + hero_w - pw - 5, ty, c["badge"])
        d.text((x + 5, ty), fit_text(c["date"], F_HERO_DATE, hero_w - 10 - pw - 4, d),
               font=F_HERO_DATE, fill=RED)
        ty += lh(F_HERO_DATE)
        ty = put_lines(d, x + 5, ty, hero_m[i][1], hero_m[i][2], INK)
        ty = put_lines(d, x + 5, ty, hero_m[i][3], F_HERO_BODY, INK)
        # WHY IT MATTERS (red label + text; first line indented, rest full width)
        d.text((x + 5, ty), "WHY IT MATTERS", font=F_WIM_T, fill=RED)
        wl = hero_m[i][4]
        lw = hero_m[i][5]
        if wl:
            d.text((x + 5 + lw, ty), wl[0], font=F_WIM, fill=INK)
            ty += lh(F_WIM)
            for extra in wl[1:]:
                d.text((x + 5, ty), extra, font=F_WIM, fill=INK)
                ty += lh(F_WIM)
        else:
            ty += lh(F_WIM)
        d.text((x + 5, ty), c["src"], font=F_HERO_SRC, fill=GREY)
    y += hero_art + hero_text + 3

    # --- mid rows: rows of 5, 5, then 3 cards stretched to full width
    rows = [(MIDS[0:5], mid_w, 4), (MIDS[5:10], mid_w, 4), (MIDS[10:13], wide_w, 4)]
    for ri, (cards, cw, gap) in enumerate(rows):
        row_h = mid_art + mid_text[ri]
        for k, c in enumerate(cards):
            x = M + k * (cw + gap)
            d.rectangle([x, y, x + cw, y + row_h], outline=LINE, width=1)
            SCENES[c["scene"]](d, x + 1, y + 1, cw - 2, mid_art - 1)
            num_badge(d, x + cw - 12, y + 12, c["n"], r=10)
            m = mid_m[ri * 5 + k] if ri < 2 else mid_m[10 + k]
            ty = y + mid_art + 2
            pw = pill_w(d, c["badge"])
            claim_pill(d, x + cw - pw - 5, ty, c["badge"])
            d.text((x + 5, ty), fit_text(c["date"], F_MID_DATE, cw - 10 - pw - 4, d),
                   font=F_MID_DATE, fill=RED)
            ty += lh(F_MID_DATE)
            ty = put_lines(d, x + 5, ty, m[1], m[2], INK)
            put_lines(d, x + 5, ty, m[3], F_MID_BODY, INK)
        y += row_h + 3

    # --- map
    d.text((M, y), "WHERE IT HAPPENED", font=F_MAP_T, fill=INK)
    d.text((M + 150, y), "pins match story numbers", font=F("DejaVuSans.ttf", 10), fill=GREY)
    y += lh(F_MAP_T)
    lx = M
    for name, cnt, col in CONTINENTS:
        d.rectangle([lx, y + 1, lx + 9, y + 10], fill=col)
        t = f"{name} {cnt}"
        d.text((lx + 11, y), t, font=F_CONT, fill=INK)
        lx += 11 + d.textlength(t, font=F_CONT) + 14
    y += lh(F_CONT) + 4
    draw_map(d, M, y, CW, map_art)
    y += map_art + 3

    # --- list 17-38, columns balanced 8/7/7
    d.text((M, y), "ALSO ON WEDNESDAY 25 NOVEMBER — 22 MORE STORIES", font=F_LIST_H, fill=INK)
    rt = "ALL 25 NOVEMBER 2026"
    d.text((W - M - d.textlength(rt, font=F_LIST_H), y), rt, font=F_LIST_H, fill=RED)
    y += lh(F_LIST_H) + 2
    cols = [LIST[0:8], LIST[8:15], LIST[15:22]]
    col_w = (CW - 2 * 16) / 3
    for ci, col in enumerate(cols):
        cx = M + ci * (col_w + 16)
        for ri, (n, badge_label, txt) in enumerate(col):
            ry = y + ri * list_row_h
            d.text((cx, ry), str(n), font=F_LIST_N, fill=INK)
            draw_glyph(d, cx + 20, ry + 1, 10, GLYPHS[(n + ci) % len(GLYPHS)],
                       GLYPH_COLS[(n + ci) % len(GLYPH_COLS)])
            pw = pill_w(d, badge_label)
            claim_pill(d, cx + col_w - pw - 2, ry, badge_label)
            max_tw = col_w - 34 - pw - 8
            txt = fit_text(txt, F_LIST, max_tw, d)
            d.text((cx + 34, ry), txt, font=F_LIST, fill=INK)
    y += 8 * list_row_h + 3

    # --- DATE CHECK
    d.rectangle([M, y, W - M, y + dc_h], outline=RED, width=2)
    d.text((M + 6, y + 3), "DATE CHECK", font=F_DC_T, fill=RED)
    put_lines(d, M + 6, y + 3 + lh(F_DC_T), dc_lines, F_DC, INK)
    y += dc_h + 2

    # --- footer: sources + legend
    d.text((M, y), "Sources: Reuters, AP, AFP, Al Jazeera, ABS, BEA, Ofgem, EC, NZX — all reported 25 November 2026.",
           font=F_FOOT, fill=GREY)
    d.text((W - M - d.textlength("THE WORLD IN ONE DAY", font=F_FOOT), y),
           "THE WORLD IN ONE DAY", font=F_FOOT, fill=GREY)
    y += lh(F_FOOT)
    d.text((M, y), LEGEND, font=F_FOOT, fill=GREY)
    y += lh(F_FOOT)
    print(f"final y={y} (target 1024)")
    return img


if __name__ == "__main__":
    img = render()
    img.save("entry.png", optimize=True)
    import os as _os
    print("bytes:", _os.path.getsize("entry.png"))
