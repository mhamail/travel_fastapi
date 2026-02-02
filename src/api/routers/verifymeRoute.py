from datetime import datetime, timedelta, timezone
from random import randint
from urllib.parse import quote_plus
from fastapi import APIRouter
from sqlmodel import select
from src.api.core.smtp import send_email
from src.api.models.userModel import EmailRequest, EmailVerifyOTPRequest, User, UserRead
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


# phone verify


@router.post("/to/{user_id}", response_model=UserRead)
def verify_me(
    user_id: int,
    user: requireAdmin,
    session: GetSession,
):

    db_user = session.get(User, user_id)

    if not db_user:
        return api_response(404, "User not found")

    db_user.verified = True
    db_user.phone = db_user.unverified_phone
    db_user.unverified_phone = None
    session.commit()
    session.refresh(db_user)
    updated_user = UserRead.model_validate(db_user)

    return api_response(
        200,
        "Verification link generated",
        {"verify_link": updated_user},
    )


# email otp send


@router.post("/send-email-otp", response_model=UserRead)
def verify_me(
    request: EmailRequest,
    session: GetSession,
):

    email = request.email.strip().lower()

    user = session.exec(select(User).where(User.email == email)).first()

    # ✅ Do NOT reveal whether email exists (security best practice)
    if not user:
        return api_response(200, "User Not Found")

    # Generate 6-digit OTP
    otp = f"{randint(100000, 999999)}"
    user.otp_code = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    session.add(user)
    session.commit()

    # Send OTP via email or SMS
    send_email(
        to_email=user.email,
        subject="Your Verification OTP",
        body=f"Your OTP code is: {otp} (valid for 10 minutes)",
    )

    return api_response(200, "If this email exists, an OTP has been sent.")


@router.post("/verify-email", response_model=UserRead)
def verify_me(
    request: EmailVerifyOTPRequest,
    session: GetSession,
):
    email = request.email.strip().lower()
    otp = request.otp.strip()

    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        return api_response(400, "Invalid email or OTP")

    expires_at = user.otp_expires_at

    # 🔐 normalize legacy naive timestamps
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if user.otp_code != otp or expires_at < datetime.now(timezone.utc):
        return api_response(400, "Invalid or expired OTP")

    user.otp_code = None  # clear OTP
    user.otp_expires_at = None
    user.email_verified = True
    user.updated_at = datetime.now(timezone.utc)

    session.add(user)
    session.commit()

    return api_response(200, "Your Email has been Verified Successfully.")
