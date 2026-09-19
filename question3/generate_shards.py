import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

N_SHARDS = 8
ROWS_PER_SHARD = 250
OUT_DIR = Path(__file__).parent / "shards"

FIRST = ["aarav", "diya", "rohan", "meera", "kabir", "ananya", "vikram", "isha", "arjun", "sara"]
LAST = ["sharma", "iyer", "khan", "patel", "reddy", "gupta", "nair", "singh", "das", "joshi"]
DOMAINS = ["gmail.com", "yahoo.co.in", "outlook.com", "iitm.ac.in", "proton.me"]
COUNTRIES = ["IN", "US", "UK", "SG", "DE", ""]  # country is OPTIONAL, blank is still valid
REQUIRED = ["user_id", "name", "email", "signup_date"]

BAD_EMAILS = [
    lambda f, l, d: f"{f}.{l}{d}",                
    lambda f, l, d: f"{f}.{l}@@{d}",             
    lambda f, l, d: f"{f}.{l}@{d.split('.')[0]}",
    lambda f, l, d: f"{f} {l}@{d}",              
    lambda f, l, d: f"@{d}",                     
    lambda f, l, d: f"{f}.{l}@.{d}",             
]


def valid_row(uid):
    f, l, d = random.choice(FIRST), random.choice(LAST), random.choice(DOMAINS)
    signup = date(2025, 1, 1) + timedelta(days=random.randint(0, 364))
    return {
        "user_id": str(uid),
        "name": f"{f.title()} {l.title()}",
        "email": f"{f}.{l}{random.randint(1, 999)}@{d}",
        "signup_date": signup.isoformat(),
        "country": random.choice(COUNTRIES),
    }


def corrupt(row):
    """Introduce exactly one defect into a valid row; returns the defect kind."""
    if random.random() < 0.5:
        f, l = row["name"].lower().split()
        row["email"] = random.choice(BAD_EMAILS)(f, l, random.choice(DOMAINS))
        return "bad_email"
    row[random.choice(REQUIRED)] = ""
    return "missing_field"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    expected = {}
    for shard in range(N_SHARDS):
        n_invalid = random.randint(5, 30)
        invalid_idx = set(random.sample(range(ROWS_PER_SHARD), n_invalid))
        rows, kinds = [], {"bad_email": 0, "missing_field": 0}
        for i in range(ROWS_PER_SHARD):
            row = valid_row(shard * 10_000 + i)
            if i in invalid_idx:
                kinds[corrupt(row)] += 1
            rows.append(row)

        with open(OUT_DIR / f"shard_{shard}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=REQUIRED + ["country"])
            w.writeheader()
            w.writerows(rows)
        expected[shard] = {"rows": ROWS_PER_SHARD, "invalid": n_invalid, **kinds}
        print(f"shard_{shard}.csv: {ROWS_PER_SHARD} rows, {n_invalid} invalid {kinds}")

    (OUT_DIR / "expected_counts.json").write_text(json.dumps(expected, indent=2))
    print(f"total invalid = {sum(v['invalid'] for v in expected.values())}")


if __name__ == "__main__":
    main()
