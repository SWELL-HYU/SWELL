"""SQLAlchemy 모델 패키지 초기화."""

from app.models.coordi import Coordi
from app.models.coordi_image import CoordiImage
from app.models.coordi_item import CoordiItem
from app.models.fitting_result import FittingResult
from app.models.fitting_result_item import FittingResultItem
from app.models.fitting_result_image import FittingResultImage
from app.models.item import Item
from app.models.item_image import ItemImage
from app.models.tag import Tag
from app.models.user import User
from app.models.user_closet_item import UserClosetItem
from app.models.user_coordi_interaction import UserCoordiInteraction
from app.models.user_coordi_view_log import UserCoordiViewLog
from app.models.user_embedding import UserEmbedding
from app.models.item_embedding import ItemEmbedding
from app.models.user_image import UserImage
from app.models.user_preferred_tag import UserPreferredTag

__all__ = [
    "User",
    "Item",
    "Coordi",
    "Tag",
    "FittingResult",
    "FittingResultItem",
    "UserImage",
    "ItemImage",
    "CoordiImage",
    "FittingResultImage",
    "CoordiItem",
    "UserCoordiInteraction",
    "UserCoordiViewLog",
    "UserClosetItem",
    "UserPreferredTag",
    "UserEmbedding",
    "ItemEmbedding",
]
