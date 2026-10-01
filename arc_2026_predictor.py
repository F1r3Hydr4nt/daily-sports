"""Rules-based finishing-order predictor: 2026 Qatar Prix de l'Arc de Triomphe.

Each runner gets 0-10 scores from hand-written rules; a weighted sum ranks them.
Inputs marked EST are estimates where no source was reachable (see notes in output).
"""

# name: (age, sex, trainer, form_class, dist_fit, ground_fit, connections, odds_decimal, odds_known)
# form_class: quality of 2026 results; dist_fit: proven at 12f/Longchamp; ground_fit: fast-ground suitability
RUNNERS = {
    "Daryz":            (4, "C", "F-H Graffard", 9.5, 10, 9, 8, 2.75, True),   # 2025 Arc winner, won Prix Foy
    "Maltese Cross":    (3, "C", "W Haggas",     9.0, 8,  8, 8, 5.5,  True),   # Derby 2nd, Grand Prix de Paris, Gt Voltigeur
    "Kalpana":          (4, "F", "A Balding",    9.5, 8,  8, 8, 8.0,  True),   # King George + Yorkshire Oaks
    "Diamond Necklace": (3, "F", "A O'Brien",    7.5, 4,  7, 9, 9.0,  True),   # 1st defeat, first try at 12f
    "Minnie Hauk":      (4, "F", "A O'Brien",    6.5, 9,  7, 9, 21.0, True),   # Arc 2nd by a head 2025; mixed 2026
    "Benvenuto Cellini":(3, "C", "A O'Brien",    7.0, 8,  7, 9, 17.0, True),   # Irish Derby, 3rd KG, 5th Niel
    "Friendly Soul":    (4, "F", "J Gosden",     7.5, 8,  7, 9, 13.0, False),  # Prix Vermeille winner (odds EST)
    "Bay City Roller":  (4, "C", "A O'Brien",    7.0, 8,  7, 9, 26.0, True),   # 2nd to Daryz in Prix Foy
    "Varandir":         (3, "C", "unknown",      6.5, 8,  7, 6, 21.0, False),  # Prix Niel winner (odds EST)
    "Saddadd":          (4, "C", "unknown",      6.0, 7,  7, 5, 34.0, False),  # Baden-Baden winner (odds EST)
    "Meisho Tabaru":    (5, "C", "Japan",        8.0, 6,  6, 5, 26.0, False),  # 2x Takarazuka; no prep, no Japanese Arc winner
    "Admire Terra":     (5, "C", "Japan",        7.0, 5,  6, 5, 34.0, False),  # Hanshin Daishoten; no prep
    "Thundering On":    (4, "C", "unknown",      5.0, 6,  6, 5, 67.0, False),
    "Arrow Eagle":      (4, "C", "unknown",      5.0, 6,  6, 5, 67.0, False),
    "Bright Light":     (4, "C", "unknown",      5.0, 6,  6, 5, 67.0, False),
    "Chestnut Rocket":  (4, "C", "unknown",      4.5, 5,  6, 5, 100.0, False),
}

W = {"form": 0.30, "dist": 0.15, "ground": 0.10, "connections": 0.10, "market": 0.35}


def trend_adjust(age, sex):
    """Rule-of-thumb Arc trends: 4yo/3yo colts dominate; fillies and 5yo+ marginally less so."""
    adj = 0.0
    if age >= 5:
        adj -= 0.4
    if age == 3 and sex == "F":
        adj += 0.2   # 3yo filly weight allowance
    return adj


def score(name, r):
    age, sex, _, form, dist, ground, conn, odds, _ = r
    market = 10 * (1 / odds) / (1 / 2.75)  # scaled so favourite = 10
    s = (W["form"] * form + W["dist"] * dist + W["ground"] * ground
         + W["connections"] * conn + W["market"] * min(market, 10))
    s += trend_adjust(age, sex)
    if name in ("Meisho Tabaru", "Admire Terra"):
        s -= 0.5     # first-ever overseas run for the Arc without a prep
    return round(s, 2)


if __name__ == "__main__":
    ranked = sorted(RUNNERS, key=lambda n: score(n, RUNNERS[n]), reverse=True)
    for i, n in enumerate(ranked, 1):
        print(f"{i:>2}. {n:<18} {score(n, RUNNERS[n]):.2f}")
