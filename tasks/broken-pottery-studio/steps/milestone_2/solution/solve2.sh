#!/bin/bash
set -euo pipefail

# Fix: senior discount boundary should be inclusive (>=), not exclusive (>)
sed -i "s/getattr(customer, 'age', 0) > SENIOR_AGE/getattr(customer, 'age', 0) >= SENIOR_AGE/" /app/pricing_service.py

# Fix event pricing: peak time requires both weekend AND evening
sed -i 's/        return is_weekend or is_evening$/        return is_weekend and is_evening/' /app/studio.py
