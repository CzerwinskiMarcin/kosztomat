from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import SourceFile, SourceProfile
from app.schemas.profiles import ProfileCreate, ProfileOut, ProfileUpdate

router = APIRouter(prefix='/profiles', tags=['profiles'])


@router.get('', response_model=list[ProfileOut])
def list_profiles(db: Session = Depends(get_db)) -> list[SourceProfile]:
    return list(db.scalars(select(SourceProfile).order_by(SourceProfile.name)))


@router.post('', response_model=ProfileOut, status_code=201)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)) -> SourceProfile:
    existing = db.scalar(select(SourceProfile).where(SourceProfile.name == payload.name))
    if existing is not None:
        raise AppError(400, 'A profile with this name already exists', 'PROFILE_NAME_TAKEN')
    profile = SourceProfile(**payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get('/{profile_id}', response_model=ProfileOut)
def get_profile(profile_id: int, db: Session = Depends(get_db)) -> SourceProfile:
    profile = db.get(SourceProfile, profile_id)
    if profile is None:
        raise AppError(404, 'Profile not found', 'PROFILE_NOT_FOUND')
    return profile


@router.put('/{profile_id}', response_model=ProfileOut)
def update_profile(
    profile_id: int, payload: ProfileUpdate, db: Session = Depends(get_db)
) -> SourceProfile:
    profile = db.get(SourceProfile, profile_id)
    if profile is None:
        raise AppError(404, 'Profile not found', 'PROFILE_NOT_FOUND')
    clash = db.scalar(
        select(SourceProfile).where(
            SourceProfile.name == payload.name, SourceProfile.id != profile_id
        )
    )
    if clash is not None:
        raise AppError(400, 'A profile with this name already exists', 'PROFILE_NAME_TAKEN')
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.delete('/{profile_id}', status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db)) -> None:
    profile = db.get(SourceProfile, profile_id)
    if profile is None:
        raise AppError(404, 'Profile not found', 'PROFILE_NOT_FOUND')
    files = list(db.scalars(select(SourceFile).where(SourceFile.profile_id == profile_id)))
    for source_file in files:
        source_file.profile_id = None
    db.delete(profile)
    db.commit()
