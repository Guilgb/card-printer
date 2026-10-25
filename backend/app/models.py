import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DeckFormat = Literal[
    "moxfield", "mtga", "mtgo", "archidekt", "deckstats",
    "simple", "scryfall_json", "cubecobra_csv",
]
Fit = Literal["stretch", "crop"]
BackMode = Literal["blank", "upload"]

_LENGTH = re.compile(r"^\d{1,2}(\.\d{1,2})?(mm|in)?$")
_SET = re.compile(r"^[a-zA-Z0-9]{2,6}$")
_LANGS = {"en", "sp", "fr", "de", "it", "pt", "jp", "kr", "ru", "cs", "ct", "ag", "ph"}


class JobOptions(BaseModel):
    format: DeckFormat = "moxfield"
    paper_size: str = "a4"
    card_size: str = "standard"
    back_mode: BackMode = "blank"

    # fetch.py
    ignore_set_and_collector_number: bool = False
    prefer_older_sets: bool = False
    prefer_set: list[str] = Field(default_factory=list, max_length=10)
    ignore_set: list[str] = Field(default_factory=list, max_length=10)
    prefer_showcase: bool = False
    prefer_extra_art: bool = False
    prefer_lang: list[str] = Field(default_factory=list, max_length=5)
    prefer_ub: bool = False
    ignore_ub: bool = False
    tokens: bool = False

    # create_pdf.py
    fit: Fit = "stretch"
    crop: str | None = None
    extend_edges: str | None = None
    show_outline: bool = False
    borderless: bool = False
    only_fronts: bool = False
    ppi: int = Field(300, ge=100, le=600)
    quality: int = Field(100, ge=50, le=100)

    @field_validator("prefer_set", "ignore_set")
    @classmethod
    def _sets(cls, v: list[str]) -> list[str]:
        for s in v:
            if not _SET.match(s):
                raise ValueError(f"código de set inválido: {s!r}")
        return v

    @field_validator("prefer_lang")
    @classmethod
    def _langs(cls, v: list[str]) -> list[str]:
        for s in v:
            if s not in _LANGS:
                raise ValueError(f"idioma inválido: {s!r}")
        return v

    @field_validator("crop", "extend_edges")
    @classmethod
    def _length(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if not _LENGTH.match(v):
            raise ValueError("use um valor como 3mm, 0.125in ou 6.5")
        return v
