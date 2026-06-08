#!/usr/bin/env python
"""Test imports for debugging."""

import sys
sys.path.insert(0, '.')

print("Testing imports...")

try:
    from ui.components import (
        render_assistant_response,
        render_hero,
        render_kpis,
        render_query_box,
        render_sample_questions,
        render_selected_history,
        render_schema_explorer,
        render_query_history_panel,
    )
    print("✓ All imports successful!")
    print(f"  - render_schema_explorer: {render_schema_explorer}")
    print(f"  - render_query_history_panel: {render_query_history_panel}")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
