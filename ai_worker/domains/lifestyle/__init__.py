"""Lifestyle guide async generation domain.

Mirrors the OCR domain — FastAPI INSERTs a ``pending`` ``lifestyle_guides``
row + RQ enqueues, ai-worker calls the LLM and UPDATEs the row to a terminal
status (``ready`` / ``no_active_meds`` / ``failed``).
"""
