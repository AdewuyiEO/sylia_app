"""All ORM models. Importing this module registers every table on Base.metadata."""
from ..db import Base
from .user import User, Subscription
from .profiles import IdentityProfile, BodyProfile
from .closet import ClothingItem
from .outfit import Outfit, OutfitItem
from .coach import CoachConversation, CoachMessage
from .integrations import CalendarConnection, WeatherCache, AffiliateRecommendation

__all__ = [
    "Base", "User", "Subscription", "IdentityProfile", "BodyProfile",
    "ClothingItem", "Outfit", "OutfitItem", "CoachConversation", "CoachMessage",
    "CalendarConnection", "WeatherCache", "AffiliateRecommendation",
]
