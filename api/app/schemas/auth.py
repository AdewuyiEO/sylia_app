from pydantic import BaseModel, EmailStr, Field


class RegionIn(BaseModel):
    """Device locale hints sent at signup so units, catalog region and copy are
    right from the first screen. All optional; the user can change them later."""
    locale: str | None = Field(default=None, max_length=35)      # BCP-47, e.g. "fr-FR"
    country: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str | None = Field(default=None, max_length=64)    # IANA
    units: str | None = Field(default=None, pattern="^(metric|imperial)$")


class SignupIn(RegionIn):
    email: EmailStr
    password: str = Field(max_length=256)
    display_name: str | None = Field(default=None, max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=256)


class AppleIn(RegionIn):
    identity_token: str
    display_name: str | None = Field(default=None, max_length=80)  # Apple only sends it on first sign-in


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str | None = None
