
# ============================================================
# TELCO CUSTOMER 360 - PYTEST LEARNING EXAMPLE
# File: tests/test_example.py
# Purpose: Understand how pytest tests work
# ============================================================


def calculate_total_amount(base_charge, extra_charge):
    return base_charge + extra_charge


def test_calculate_total_amount():
    result = calculate_total_amount(100, 20)

    assert result == 120
