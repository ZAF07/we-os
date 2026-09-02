"""The questionnaire: the seed question set, completeness, and Brand DNA rendering.

The admin-curated question set is the single artifact driving three things — the
onboarding wizard, the shape of the rendered Brand DNA, and what the DNA Gate
enforces as Required — so none of the three can drift from the others
(ADR-0018). This package holds the pure domain: the code-shipped seed version,
the completeness report, and the markdown projection. Where a published version
and a tenant's answers are *stored* is the adapters' business.
"""

from __future__ import annotations

from marketing_os.questionnaire.completeness import completeness, required_dna_fields
from marketing_os.questionnaire.render import render_brand_dna
from marketing_os.questionnaire.seed import (
    SECTION_ORDER,
    SEED_PUBLISHED_AT,
    SEED_QUESTIONNAIRE,
    SEED_VERSION,
)

__all__ = [
    "SECTION_ORDER",
    "SEED_PUBLISHED_AT",
    "SEED_QUESTIONNAIRE",
    "SEED_VERSION",
    "completeness",
    "render_brand_dna",
    "required_dna_fields",
]
