from pathlib import Path
from typing import Dict, List, Optional

import tomllib


class TemplateManager:
    def __init__(self, template_path: str):
        self.template_path = template_path
        # Load config (fixed fields + rendering settings) from project templates directory
        # Always read from bundled templates, not from user directory
        config_path = Path(__file__).parent.parent.parent / "templates" / "config.toml"

        self._config = self._load_toml(str(config_path))
        # Load template (variable fields)
        self._template = self._load_toml(template_path)
        # Merge: config fields first, then template fields
        self._cfg = self._merge_config_and_template()

    def _load_toml(self, path: str) -> dict:
        with open(path, "rb") as f:
            return tomllib.load(f)

    def _merge_config_and_template(self) -> dict:
        """Merge config (fixed fields + settings) with template (variable fields)."""
        merged = {}
        # Copy rendering settings from config
        for key in ("separator", "kv_sep", "trim_empty"):
            if key in self._config:
                merged[key] = self._config[key]

        # Add fixed fields from config first (preserves order)
        for label, item in self._config.items():
            if label not in ("separator", "kv_sep", "trim_empty"):
                if isinstance(item, dict) and ("key" in item or "value" in item):
                    merged[label] = item

        # Add variable fields from template
        for label, item in self._template.items():
            if isinstance(item, dict) and ("key" in item or "value" in item):
                merged[label] = item

        return merged

    @property
    def separator(self) -> str:
        return self._cfg.get("separator", "|")

    @property
    def kv_sep(self) -> str:
        return self._cfg.get("kv_sep", ":")

    @property
    def trim_empty(self) -> bool:
        return bool(self._cfg.get("trim_empty", True))

    def get_fields(self) -> List[Dict[str, str]]:
        """
        Return ordered field dicts for rendering: [{key, value, label?, required?, pattern?}].

        Supports three TOML shapes:
        1) Array of tables: [[fields]]
        2) Table of tables: [fields.Label]
        3) Top-level tables per field: [Label]
        """
        cfg = self._cfg
        result: List[Dict[str, str]] = []

        # 1) [[fields]]
        fields = cfg.get("fields")
        if isinstance(fields, list):
            # Assume items are already dicts with the right keys
            return list(fields)

        # 2) [fields.Label]
        if isinstance(fields, dict):
            for label, item in fields.items():
                if isinstance(item, dict) and ("key" in item or "value" in item):
                    normalized = {
                        "key": item.get("key", ""),
                        "value": item.get("value", ""),
                    }
                    if "label" in item:
                        normalized["label"] = item["label"]
                    else:
                        normalized["label"] = label
                    if "required" in item:
                        normalized["required"] = item["required"]
                    if "pattern" in item:
                        normalized["pattern"] = item["pattern"]
                    result.append(normalized)
            if result:
                return result

        # 3) Top-level [Label]
        known_top = {"separator", "kv_sep", "trim_empty"}
        for label, item in cfg.items():
            if label in known_top:
                continue
            if isinstance(item, dict) and ("key" in item or "value" in item):
                normalized = {
                    "key": item.get("key", ""),
                    "value": item.get("value", ""),
                    "label": item.get("label", label),
                }
                if "required" in item:
                    normalized["required"] = item["required"]
                if "pattern" in item:
                    normalized["pattern"] = item["pattern"]
                result.append(normalized)

        return result

    def render_payload(
        self, overrides: Optional[Dict[str, str]] = None, include_extras: bool = True
    ) -> str:
        """
        Build the payload string using fields order and optional overrides.

        - overrides: mapping of key->value to replace defaults
        - include_extras: if True, include overrides for keys not in template at the end
        """
        overrides = overrides or {}
        out: List[str] = []
        seen: set[str] = set()

        for item in self.get_fields():
            field_key = item["key"]
            name = field_key
            value = overrides.get(field_key, item.get("value", ""))
            if value is None:
                value = ""
            if self.trim_empty and str(value) == "":
                continue
            out.append(f"{name}{self.kv_sep}{value}")
            seen.add(field_key)

        if include_extras:
            for k, v in overrides.items():
                if k in seen:
                    continue
                if self.trim_empty and (v is None or str(v) == ""):
                    continue
                out.append(f"{k}{self.kv_sep}{v}")

        return self.separator.join(out)
