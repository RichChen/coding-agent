"""Built-in handlers."""

from __future__ import annotations


def echo_handler(payload: dict) -> dict:
    return {"echo": payload.get("text", "")}


def uppercase_handler(payload: dict) -> dict:
    text = payload.get("text", "")
    return {"text": text.upper()}


def length_handler(payload: dict) -> dict:
    text = payload.get("text", "")
    return {"length": len(text)}
