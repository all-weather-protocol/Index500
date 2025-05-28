import math


# Calculate the security score for a single protocol layer
# Higher TVL and age → higher security score
def security_score(tvl_million, age_days):
    return math.log(tvl_million + 10) * math.log(age_days + 10)


# Harmonic mean of security scores
# This gives more weight to weak layers, and prevents a strong one from masking risk:
def effective_risk(layers):
    n = len(layers)
    harmonic_mean = n / sum(
        1 / security_score(layer["tvl"], layer["age"]) for layer in layers
    )
    return 1 / harmonic_mean


# Calculate allocation score using a simplified Kelly-style logic
# Higher APR and lower risk → higher allocation score
def alloc_score(apr, risk):
    return math.log(apr + 1) / risk


# Main function: input list of assets, output allocation plan
def calculate_allocations(assets):
    scores = []
    for asset in assets:
        risk = effective_risk(asset["layers"])
        score = alloc_score(asset["apr"], risk)
        scores.append(
            {"name": asset["name"], "apr": asset["apr"], "risk": risk, "score": score}
        )

    # Normalize all scores to get allocation percentages
    total_score = sum(item["score"] for item in scores)
    for item in scores:
        item["allocation_pct"] = item["score"] / total_score * 100

    return scores


# ✅ Example: PT-wstETH (Pendle + Lido), wstETH, stables on Aave
# assets = [
#     {
#         "name": "PT-eeth@Pendle",
#         "apr": 4.19,
#         "layers": [
#             { "name": "Pendle", "tvl": 4700, "age": 4 },
#             { "name": "Etherfi",   "tvl": 6400, "age": 2 }
#         ]
#     },
#     {
#         "name": "PT-wsteth@Pendle",
#         "apr": 2.86,
#         "layers": [
#             { "name": "Pendle", "tvl": 4700, "age": 4 },
#             { "name": "Lido", "tvl": 23000, "age": 5 }
#         ]
#     },
#     # {
#     #     "name": "wstETH@Lido",
#     #     "apr": 2.86,
#     #     "layers": [
#     #         { "name": "Lido", "tvl": 23000, "age": 5 }
#     #     ]
#     # },
#     {
#         "name": "eth@aave",
#         "apr": 2.05,
#         "layers": [
#             { "name": "Aave", "tvl": 24000, "age": 5 }
#         ]
#     },
#     {
#         "name": "mseth@aerodrome",
#         "apr": 4.51,
#         "layers": [
#             { "name": "Aerodrome", "tvl": 251, "age": 2 },
#             { "name": "Metronome Synth", "tvl": 976, "age": 2 }
#         ]
#     }
# ]
assets = [
    {
        "name": "ousdt",
        "apr": 9.37,
        "layers": [{"name": "openusdt", "tvl": 2, "age": 0.2}],
    },
    {"name": "aster", "apr": 25, "layers": [{"name": "bold", "tvl": 348, "age": 3}]},
    {"name": "bold", "apr": 14, "layers": [{"name": "bold", "tvl": 315, "age": 4}]},
    {
        "name": "gusdc",
        "apr": 9.21,
        "layers": [{"name": "gains", "tvl": 28.33, "age": 3}],
    },
    {
        "name": "msusd",
        "apr": 8.81,
        "layers": [{"name": "gains", "tvl": 20.23, "age": 2}],
    },
    {"name": "susd", "apr": 9.21, "layers": [{"name": "synx", "tvl": 97.23, "age": 7}]},
]

# ✅ Run the calculation and print the result
results = calculate_allocations(assets)
# Sort by allocation percentage in descending order
results_sorted = sorted(results, key=lambda x: x["allocation_pct"], reverse=True)
for r in results_sorted:
    print(f"{r['name']}:")
    print(f"  APR: {r['apr']*100:.2f}%")
    print(f"  Effective Risk: {r['risk']:.6f}")
    print(f"  Score: {r['score']:.4f}")
    print(f"  Suggested Allocation: {r['allocation_pct']:.2f}%")
    print()
