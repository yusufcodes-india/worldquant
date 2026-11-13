#!/usr/bin/env python3
"""
Prepares Supervised Fine-Tuning (SFT) dataset for Google Gemini models
using validated, high-performing WorldQuant BRAIN alphas from alphas.json & alphas1.json.
Output: data/gemini_tuning_dataset.jsonl (Google AI Studio / Vertex AI tuning format)
"""

import sys
import os
import json

# Ensure backend on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.engine.fast_expression import ExpressionValidator

def prepare_tuning_dataset():
    validator = ExpressionValidator(max_operators=64, max_fields=20)
    files = ["/Users/yusuftarwala/alphas1.json", "/Users/yusuftarwala/alphas.json"]

    tuning_examples = []
    seen_hashes = set()

    for fpath in files:
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            data = json.load(f)

        for item in data.get("results", []):
            regular = item.get("regular") or {}
            code = regular.get("code")
            if not code:
                continue

            # Strip comments or trailing whitespace
            clean_code = code.strip()
            
            # Validate code syntax & extract metrics
            rep = validator.validate(clean_code)
            if not rep.is_valid:
                continue

            if rep.normalized_hash in seen_hashes:
                continue
            seen_hashes.add(rep.normalized_hash)

            is_metrics = item.get("is") or {}
            sharpe = is_metrics.get("sharpe", 0.0)
            fitness = is_metrics.get("fitness", 0.0)
            ops = rep.estimated_operators
            fields = rep.estimated_fields
            category = item.get("category") or "Quantitative Factor"

            # Filter for quality alphas: Sharpe >= 1.20 and Fitness >= 0.80
            if sharpe >= 1.20 and fitness >= 0.80:
                # Construct instruction prompt
                field_list = ", ".join(rep.unique_fields)
                prompt = (
                    f"Design a WorldQuant BRAIN Fast Expression quantitative alpha in {category}. "
                    f"Constraints: at most {max(8, ops)} operators and at most {max(4, fields)} data fields. "
                    f"Use verified fields such as {field_list}. "
                    f"The expression must be mathematically robust, pass sub-universe tests, and exhibit strong risk-adjusted returns."
                )

                tuning_examples.append({
                    "text_input": prompt,
                    "output": clean_code,
                    "metadata": {
                        "alpha_id": item.get("id"),
                        "sharpe": sharpe,
                        "fitness": fitness,
                        "operator_count": ops,
                        "field_count": fields,
                        "status": item.get("status")
                    }
                })

    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. JSONL file for Google AI Studio / Vertex AI tuning
    jsonl_path = os.path.join(out_dir, "gemini_tuning_dataset.jsonl")
    with open(jsonl_path, "w") as f:
        for ex in tuning_examples:
            # Format: {"text_input": ..., "output": ...}
            line_data = {"text_input": ex["text_input"], "output": ex["output"]}
            f.write(json.dumps(line_data) + "\n")

    # 2. Complete JSON with metadata for inspection & few-shot injection
    json_path = os.path.join(out_dir, "gemini_tuning_dataset.json")
    with open(json_path, "w") as f:
        json.dump(tuning_examples, f, indent=2)

    print(f"Dataset preparation complete:")
    print(f"  - Extracted {len(tuning_examples)} high-Sharpe (>= 1.20) training examples.")
    print(f"  - Saved JSONL: {jsonl_path}")
    print(f"  - Saved JSON:  {json_path}")
    return tuning_examples

if __name__ == "__main__":
    prepare_tuning_dataset()
