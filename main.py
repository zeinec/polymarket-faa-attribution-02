#!/usr/bin/env python3
"""Session 4 shipped design: retained v5 RMS fan after v2 practice regressions."""

import json
import math
import os
from pathlib import Path

Z_VALUES = (-1.644854, -0.67449, 0.0, 0.67449, 1.644854)
WIDTH_FACTORS = (1.1, 0.85, 1.0, 0.35, 1.3)


def forecast_case(case):
    markets = case["markets"]
    horizon = case["horizon_minutes"]
    prices_by_market = [market["prices"] for market in markets]
    last_prices = [float(prices[-1]) if prices else 0.5
                   for prices in prices_by_market]
    total_price = sum(last_prices)
    consistency_targets = ([price / total_price for price in last_prices]
                           if total_price > 0.0 else last_prices)
    sigmas = []
    last_moves = []
    for prices in prices_by_market:
        recent = [float(value) for value in prices[-121:]]
        changes = [recent[index] - recent[index - 1]
                   for index in range(1, len(recent))]
        sigma = (math.sqrt(sum(change * change for change in changes)
                           / len(changes)) if changes else 0.0)
        sigmas.append(min(0.01, max(0.0005, sigma)))
        last_moves.append(changes[-1] if changes else 0.0)

    sum_gate = min(1.0, max(0.0, (total_price - 0.8) / 0.25))
    decay_k = 96.0 * sum_gate
    results = []
    for market_index, market in enumerate(markets):
        last_price = last_prices[market_index]
        sigma = sigmas[market_index]
        move = last_moves[market_index]
        quantile_rows = []
        for minute in range(1, horizon + 1):
            phase = 1.0 - math.exp(-minute / 60.0)
            center = last_price + 0.60 * phase * (
                consistency_targets[market_index] - last_price)
            if move > 0.0:
                center -= 0.5 * move
            elif move < 0.0:
                center += 0.5 * move
            spread = sigma * minute ** 0.35
            values = []
            for z_value, width in zip(Z_VALUES, WIDTH_FACTORS):
                value = center + z_value * width * spread
                if z_value == 0.0:
                    value *= math.exp(-decay_k * sigma * sigma * minute / 2.0)
                values.append(min(1.0, max(0.0, round(value, 6))))
            values.sort()
            quantile_rows.append(values)
        results.append({"id": market["id"], "q": quantile_rows})
    return {"forecasts": results}


def main():
    input_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    for input_path in sorted(input_dir.glob("*.in"), key=lambda path: path.name):
        with input_path.open(encoding="utf-8") as source:
            case = json.load(source)
        encoded = json.dumps(forecast_case(case), separators=(",", ":"),
                             allow_nan=False) + "\n"
        (output_dir / (input_path.stem + ".out")).write_text(encoded,
                                                               encoding="utf-8")


if __name__ == "__main__":
    main()
