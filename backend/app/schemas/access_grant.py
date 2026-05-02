import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.access_grant import AccessScopeKind
from app.models.stream import Stream


class AccessGrantCreate(BaseModel):
    user_id: uuid.UUID
    scope_kind: AccessScopeKind
    scope_stream: Optional[Stream] = None
    scope_owner_profile_id: Optional[uuid.UUID] = None
    scope_property_id: Optional[uuid.UUID] = None
    can_view_observations: bool = True
    can_view_chain_audit: bool = False
    can_view_financials: bool = False
    can_view_personal_data: bool = False
    expires_at: Optional[datetime] = None

    @model_validator(mode="after")
    def _scope_target_matches_kind(self):
        if self.scope_kind == AccessScopeKind.STREAM and self.scope_stream is None:
            raise ValueError("scope_kind=stream requires scope_stream")
        if (
            self.scope_kind == AccessScopeKind.OWNER_PROFILE
            and self.scope_owner_profile_id is None
        ):
            raise ValueError("scope_kind=owner_profile requires scope_owner_profile_id")
        if (
            self.scope_kind == AccessScopeKind.PROPERTY
            and self.scope_property_id is None
        ):
            raise ValueError("scope_kind=property requires scope_property_id")
        return self


class AccessGrantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    scope_kind: AccessScopeKind
    scope_stream: Optional[Stream]
    scope_owner_profile_id: Optional[uuid.UUID]
    scope_property_id: Optional[uuid.UUID]
    can_view_observations: bool
    can_view_chain_audit: bool
    can_view_financials: bool
    can_view_personal_data: bool
    granted_by: uuid.UUID
    granted_at: datetime
    expires_at: Optional[datetime]
