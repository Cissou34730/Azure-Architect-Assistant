"""Service layer for architect profile persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.settings.contracts import ArchitectProfileResponseContract
from app.features.settings.domain.architect_profile import ArchitectProfile
from app.models.project import ArchitectProfileRecord

_PROFILE_ROW_ID = "default"


class ArchitectProfileService:
    """Read and persist the installation-scoped architect profile."""

    async def get_profile(self, db: AsyncSession) -> ArchitectProfileResponseContract:
        record = await self._get_record(db)
        if record is None:
            return ArchitectProfileResponseContract(profile=ArchitectProfile(), updated_at=None)

        return ArchitectProfileResponseContract(
            profile=ArchitectProfile.model_validate(json.loads(record.profile_json)),
            updated_at=record.updated_at,
        )

    async def update_profile(
        self,
        *,
        profile: ArchitectProfile,
        db: AsyncSession,
    ) -> ArchitectProfileResponseContract:
        record = await self._get_record(db)
        updated_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(profile.model_dump(mode="json", by_alias=True))

        if record is None:
            record = ArchitectProfileRecord(
                id=_PROFILE_ROW_ID,
                profile_json=payload,
                updated_at=updated_at,
            )
            db.add(record)
        else:
            record.profile_json = payload
            record.updated_at = updated_at

        await db.flush()
        return ArchitectProfileResponseContract(profile=profile, updated_at=updated_at)

    async def _get_record(self, db: AsyncSession) -> ArchitectProfileRecord | None:
        result = await db.execute(
            select(ArchitectProfileRecord).where(ArchitectProfileRecord.id == _PROFILE_ROW_ID)
        )
        return result.scalar_one_or_none()

