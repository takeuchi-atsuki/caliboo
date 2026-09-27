from typing import Literal

from pydantic import BaseModel

Tone = Literal["green", "blue", "purple", "pink", "orange"]


class HomeUser(BaseModel):
    name: str
    streakDays: int


class HomeHero(BaseModel):
    message: str


class HomeCertification(BaseModel):
    name: str
    achievementPercent: int


class HomeStrength(BaseModel):
    label: str
    tone: Tone


class HomeShortcut(BaseModel):
    icon: str
    title: str
    description: str
    to: str
    tone: Tone


class HomeSummary(BaseModel):
    user: HomeUser
    hero: HomeHero
    certification: HomeCertification
    strengths: list[HomeStrength]
    shortcuts: list[HomeShortcut]
