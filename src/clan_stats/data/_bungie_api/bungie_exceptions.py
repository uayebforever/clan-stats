from typing import Optional

from clan_stats.data._bungie_api.bungie_enums import MembershipType


class PrivacyError(RuntimeError):
    
    def __init__(self, message: str,
                 membership_id: Optional[int] = None,
                 membership_type=Optional[MembershipType],
                 original_exception: Optional[BaseException] = None):
        super().__init__(message)
        self.message = message
        self.membership_id = membership_id
        self.membership_type = membership_type
        self.original_exception = original_exception


