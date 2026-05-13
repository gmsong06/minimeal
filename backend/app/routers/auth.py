from fastapi import APIRouter, HTTPException

from ..schemas.meal import (
    AuthLoginRequest,
    AuthLoginResponse,
    SeededAccount,
)
from ..services.storage import get_storage

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/accounts", response_model=list[SeededAccount])
def get_seeded_accounts():
    try:
        return [SeededAccount(**account) for account in get_storage().list_seeded_accounts()]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/login", response_model=AuthLoginResponse)
def login(request: AuthLoginRequest):
    try:
        authenticated_user = get_storage().authenticate(
            request.username, request.password
        )
        if not authenticated_user:
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        return AuthLoginResponse(**authenticated_user)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
