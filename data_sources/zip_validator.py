# data_sources/zip_validator.py
import re


def is_valid_us_zip(zip_code: str) -> bool:
    return bool(re.fullmatch(r"\d{5}", zip_code.strip()))


def normalize_zip(zip_code: str) -> str:
    return zip_code.strip()
