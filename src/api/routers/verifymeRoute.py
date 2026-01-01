from urllib.parse import quote_plus
from fastapi import APIRouter
from src.api.models.userModel import User
from src.api.core import (
    GetSession,
    api_response,
    requireSignin,
    requireAdmin,
    requirePermission,
    verifiedUser,
)

router = APIRouter(prefix="/verify", tags=["verify"])

phone = "923355144441"


@router.post("/me")
def verify_me(
    user: requireSignin,
    session: GetSession,
):
    """
    Generate WhatsApp verification link and return it to frontend
    """
    if user.get("verified") is True and user.get("phone") is not None:
        api_response(
            400,
            "User is already verified",
        )
    user_id = user.get("id")
    db_user = session.get(User, user_id)
    email = user.get("email")
    unverified_phone = db_user.unverified_phone  # user's phone (receiver)

    # Message text (what user will see in WhatsApp)
    message = (
        f"Verify my account\n\n"
        f"User ID: {user_id}\n"
        f"Email: {email}\n"
        f"Phone: {unverified_phone}"
    )

    print("phone", user)

    whatsapp_link = f"https://wa.me/{phone}?text={quote_plus(message)}"

    return api_response(
        200,
        "Verification link generated",
        {"verify_link": whatsapp_link},
    )
