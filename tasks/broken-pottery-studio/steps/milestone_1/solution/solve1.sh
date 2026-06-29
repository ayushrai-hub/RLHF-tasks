#!/bin/bash
set -euo pipefail

# Fix pricing: tax applied to discounted total, not subtotal
sed -i 's/tax_amount = self._compute_tax(subtotal)/tax_amount = self._compute_tax(discounted_total)/' /app/pricing_service.py

# Fix pricing: group discount is percentage, not flat amount
sed -i 's/discount_amount += 15\.0/discount_amount += subtotal * 0.15/' /app/pricing_service.py

# Fix pricing: loyalty discount calculated from original subtotal independently
sed -i '/is_returning_student/{n;/remaining = subtotal/d}' /app/pricing_service.py
sed -i 's/discount_amount += remaining \* 0\.1$/discount_amount += subtotal * 0.1/' /app/pricing_service.py
