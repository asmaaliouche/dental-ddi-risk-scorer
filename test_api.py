import httpx, json

base = "http://localhost:8000"

# Test 1: health
r = httpx.get(f"{base}/health")
print("=== /health ===")
print(r.text)

# Test 2: dental drugs
r = httpx.get(f"{base}/dental-drugs")
d = r.json()
print(f"\n=== /dental-drugs ({d['total']} drugs) ===")
for drug in d["drugs"][:5]:
    print(f"  {drug['name']:25} | {drug['category']}")

# Test 3: patient drugs available
r = httpx.get(f"{base}/patient-drugs")
d = r.json()
print(f"\n=== /patient-drugs ({d['total']} available) — sample: {d['drugs'][:5]}")

# Test 4: check — patient on warfarin + atorvastatin
payload = {"patient_drugs": ["warfarin", "atorvastatin"]}
r = httpx.post(f"{base}/check", json=payload)
d = r.json()
print(f"\n=== POST /check (warfarin + atorvastatin) — {d['total_interactions']} interactions ===")
print(f"Not found: {d['patient_drugs_not_found']}")
for i in d["interactions"][:8]:
    ae = " | ".join(i["top_adverse_effects"][:2])
    print(f"  [{i['severity_bin'].upper():8}] score={i['risk_score']:5.1f}  {i['dental_drug_display']:25} x {i['patient_drug']:15} -> {ae}")
