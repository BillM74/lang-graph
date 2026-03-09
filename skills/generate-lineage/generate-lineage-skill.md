---
name: generate-lineage
description: Regenerates .claude/FILE_INDEX.md and .claude/LINEAGE.md from the dbt manifest. Use when: "regenerate lineage", "update lineage", "refresh file index", "update file index", "models changed", "added new model", "manifest out of date", after adding or removing dbt models.
---

# Generate Lineage

Regenerates the codebase navigation indexes that all agents use for efficient traversal.

## What It Produces

| File | Purpose |
|------|---------|
| `.claude/FILE_INDEX.md` | Compact lookup table: model → path → deps → used-by. Also seeds and sources. |
| `.claude/LINEAGE.md` | Full DAG grouped by layer with descriptions. |

## When to Run

- After adding, removing, or renaming any dbt model
- After changing `ref()` or `source()` calls
- After seed file changes that affect dependencies
- When lineage files feel stale (check the `**Generated**` date at the top)

## Steps

1. Ensure the manifest is current:

```bash
dbt parse
```

2. Run the generation script:

```bash
python3 .claude/scripts/generate-lineage.py
```

3. Verify output:
   - Check the generated date in both files
   - Spot-check a recently changed model's entry

## Notes

- The script reads only from `target/manifest.json` — no Snowflake connection needed
- Both files are gitignored-safe (they can be committed or not, your choice)
- If `dbt parse` fails, fix the dbt error first — the script needs a valid manifest
