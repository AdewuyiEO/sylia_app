"""All ORM models. Importing this module registers every table on Base.metadata."""
from ..db import Base
from .user import User, Subscription, RevokedToken
from .profiles import IdentityProfile, BodyProfile
from .closet import ClothingItem
from .outfit import Outfit, OutfitItem
from .coach import CoachConversation, CoachMessage
from .integrations import CalendarConnection, WeatherCache, AffiliateRecommendation
from .catalog import Brand, Product
from .tryon import TryOnProfile, TryOnRender

__all__ = [
    "Base", "User", "Subscription", "IdentityProfile", "BodyProfile",
    "ClothingItem", "Outfit", "OutfitItem", "CoachConversation", "CoachMessage",
    "CalendarConnection", "WeatherCache", "AffiliateRecommendation",
    "RevokedToken", "Brand", "Product", "TryOnProfile", "TryOnRender",
]
