"""The Typer command-line interface — thin: parse, delegate to services, display.

Typer maps every CLI option to one function parameter, so command functions are the
single, documented exception to the 3-parameter rule: they turn their options into a
settings layer right away and delegate to `media_dedup.services`.
"""

from __future__ import annotations
