#!/bin/bash
# Test Coverage Analysis Script
# Identifies models with missing or insufficient test coverage

echo "=== dbt Test Coverage Report ==="
echo ""

# Count total models and tests
total_models=$(dbt list --resource-type model --output name 2>/dev/null | wc -l)
total_tests=$(dbt list --resource-type test --output name 2>/dev/null | wc -l)

echo "Total Models: $total_models"
echo "Total Tests: $total_tests"
echo ""

# Models without any tests
echo "=== Models Without Tests ==="
dbt list --resource-type model --output name 2>/dev/null | while read model; do
  test_count=$(dbt list --select "$model" --resource-type test --output name 2>/dev/null | wc -l)
  if [ "$test_count" -eq 0 ]; then
    echo "❌ $model (0 tests)"
  fi
done

echo ""
echo "=== Test Coverage by Model ==="
dbt list --resource-type model --output name 2>/dev/null | while read model; do
  test_count=$(dbt list --select "$model" --resource-type test --output name 2>/dev/null | wc -l)

  # Determine coverage level
  if [ "$test_count" -eq 0 ]; then
    status="❌"
  elif [ "$test_count" -lt 3 ]; then
    status="⚠️"
  else
    status="✅"
  fi

  echo "$status $model ($test_count tests)"
done

echo ""
echo "=== Target Coverage by Model Type ==="
echo "Staging:   2+ tests (PK unique + not_null)"
echo "Activity:  3+ tests (PK, occurred_at, type)"
echo "Fact:      4+ tests (PK, FKs, amounts)"
echo "Dimension: 3+ tests (PK, name, status)"
echo "Net:       5+ tests (composite PK, bi-temporal, formulas)"
