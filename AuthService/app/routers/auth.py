from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import hashlib
from datetime import timedelta, datetime
import httpx
import secrets

from typing import List, Optional

from ..database import get_db
from ..models import User, Friendship, PasswordResetToken
from ..schemas import (
    UserCreate, UserLogin, UserOut, UserSearchOut, Token, FriendsList, FriendUser, RespondRequest,
    ForgotPasswordRequest, ResetPasswordRequest, AdminStatusUpdate, ChangePasswordRequest
)
from ..auth import verify_password, get_password_hash, create_access_token
from ..dependencies import get_current_user, get_current_admin
from ..config import settings
from ..rate_limit import limiter
from ..email_utils import send_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Endpoints that take `request: Request` as the first parameter do so because
# slowapi requires it to identify the caller's IP, even though the route body
# never uses it directly.



@router.post("/register", response_model=UserOut)
@limiter.limit("10/minute")
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    # Check if username or email already exists
    existing_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    # Admin status is never granted through this endpoint — see bootstrap_admin.py
    # for creating the first admin, and PATCH /auth/users/{id}/admin-status for
    # existing admins promoting others. A shared code reachable over the network
    # is a standing liability; this isn't.
    hashed = get_password_hash(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed, is_admin=False)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": str(db_user.id)})  # store user ID
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/profile", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user





# ── Password reset ──────────────────────────────────────────────────────

RESET_TOKEN_LIFETIME_MINUTES = 30

@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Always return the same response whether or not the email is registered —
    # otherwise this endpoint becomes a way to check who has an account here.
    generic_response = {"detail": "If that email is registered, a reset link has been sent."}

    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        return generic_response

    # Invalidate any earlier outstanding tokens for this user before issuing a new one
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete(synchronize_session=False)

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=RESET_TOKEN_LIFETIME_MINUTES),
    )
    db.add(reset_token)
    db.commit()

    reset_link = f"{settings.FRONTEND_URL}/?reset_token={token}"
    send_email(
        to=user.email,
        subject="Reset your Reading List password",
        body=(
            f"Hi {user.username},\n\n"
            f"Someone (hopefully you) asked to reset your Reading List password.\n\n"
            f"Reset it here (expires in {RESET_TOKEN_LIFETIME_MINUTES} minutes):\n{reset_link}\n\n"
            f"If you didn't request this, you can ignore this email — your password won't change."
        ),
    )
    return generic_response

@router.post("/change-password")
@limiter.limit("5/minute")
def change_password(request: Request, body: ChangePasswordRequest,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if body.old_password == body.new_password:
        raise HTTPException(status_code=400, detail="New password must differ from the current one")
    current_user.hashed_password = get_password_hash(body.new_password)
    db.commit()
    return {"detail": "Password updated"}


@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    reset_token = db.query(PasswordResetToken).filter(PasswordResetToken.token == token_hash).first()
    if not reset_token or reset_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")

    user.hashed_password = get_password_hash(body.new_password)
    # Used tokens (and any other outstanding ones for this user) are gone once used
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete(synchronize_session=False)
    db.commit()
    return {"detail": "Password updated — you can log in with your new password now."}

# Admin-only: full user list with management controls in the web app.
@router.get("/users", response_model=List[UserOut])
def list_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()

# Any logged-in user can search for people to friend. Keep the response limited to
# public identifying information; /users retains full details for admins.
@router.get("/search", response_model=List[UserSearchOut])
def search_users(q: str = Query(..., min_length=2), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(User).filter(
        User.id != current_user.id,
        User.username.ilike(f"%{q.strip()}%"),
    )
    return query.order_by(User.username).limit(50).all()

# Admin-only: remove a user entirely — their account, friendships, and books.
@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You can't delete your own account")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    db.query(Friendship).filter(
        or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id)
    ).delete(synchronize_session=False)

    try:
        httpx.delete(f"{settings.LIBRARY_SERVICE_URL}/books/internal/by-user/{user_id}", timeout=5.0)
    except httpx.HTTPError:
        # Don't block the account deletion if LibraryService is unreachable — the
        # user record and friendships are still removed; books would be orphaned
        # but inaccessible since no account can authenticate as that user anymore.
        pass

    db.delete(target)
    db.commit()
    return {"detail": f"Deleted {target.username}"}

# Admin-only: promote or revoke another user's admin status. This, plus
# bootstrap_admin.py (run with server access, not over HTTP), replaces the old
# admin-registration-code flow — there's no standing secret to leak anymore.
@router.patch("/users/{user_id}/admin-status", response_model=UserOut)
def set_admin_status(user_id: int, body: AdminStatusUpdate, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if not body.is_admin and target.is_admin:
        remaining_admins = db.query(User).filter(User.is_admin == True, User.id != user_id).count()
        if remaining_admins == 0:
            raise HTTPException(status_code=400, detail="Can't remove the last admin — promote someone else first")

    target.is_admin = body.is_admin
    db.commit()
    db.refresh(target)
    return target

# ── Friendships ──────────────────────────────────────────────────────────

@router.post("/friends/request/{username}")
def send_friend_request(username: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if username == current_user.username:
        raise HTTPException(status_code=400, detail="You can't friend yourself")

    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == target.id),
            and_(Friendship.requester_id == target.id, Friendship.addressee_id == current_user.id),
        )
    ).first()
    if existing:
        detail = "You're already friends" if existing.status == "accepted" else "A request is already pending"
        raise HTTPException(status_code=400, detail=detail)

    friendship = Friendship(requester_id=current_user.id, addressee_id=target.id, status="pending")
    db.add(friendship)
    db.commit()
    return {"detail": f"Friend request sent to {username}"}

@router.post("/friends/{friendship_id}/respond")
def respond_friend_request(friendship_id: int, body: RespondRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    friendship = db.query(Friendship).filter(Friendship.id == friendship_id).first()
    if not friendship:
        raise HTTPException(status_code=404, detail="Request not found")
    if friendship.addressee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the recipient can respond to this request")
    if friendship.status != "pending":
        raise HTTPException(status_code=400, detail="This request has already been handled")

    if body.action == "accept":
        friendship.status = "accepted"
        db.commit()
        return {"detail": "Friend request accepted"}
    elif body.action == "decline":
        db.delete(friendship)
        db.commit()
        return {"detail": "Friend request declined"}
    else:
        raise HTTPException(status_code=400, detail="action must be 'accept' or 'decline'")

@router.delete("/friends/{friendship_id}")
def remove_friendship(friendship_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    friendship = db.query(Friendship).filter(Friendship.id == friendship_id).first()
    if not friendship:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.id not in (friendship.requester_id, friendship.addressee_id):
        raise HTTPException(status_code=403, detail="Not your friendship to remove")
    db.delete(friendship)
    db.commit()
    return {"detail": "Removed"}

@router.get("/friends", response_model=FriendsList)
def list_friends(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Friendship).filter(
        or_(Friendship.requester_id == current_user.id, Friendship.addressee_id == current_user.id)
    ).all()

    friends, incoming, outgoing = [], [], []
    for f in rows:
        other_id = f.addressee_id if f.requester_id == current_user.id else f.requester_id
        other = db.query(User).filter(User.id == other_id).first()
        if not other:
            continue
        entry = FriendUser(friendship_id=f.id, id=other.id, username=other.username)
        if f.status == "accepted":
            friends.append(entry)
        elif f.status == "pending" and f.addressee_id == current_user.id:
            incoming.append(entry)
        elif f.status == "pending" and f.requester_id == current_user.id:
            outgoing.append(entry)

    return FriendsList(friends=friends, incoming_requests=incoming, outgoing_requests=outgoing)

# Internal, unauthenticated check used by LibraryService (trusted local network) to verify
# two users are friends before it shares one user's books with the other.
@router.get("/internal/are-friends")
def are_friends(user_a: int, user_b: int, db: Session = Depends(get_db)):
    row = db.query(Friendship).filter(
        Friendship.status == "accepted",
        or_(
            and_(Friendship.requester_id == user_a, Friendship.addressee_id == user_b),
            and_(Friendship.requester_id == user_b, Friendship.addressee_id == user_a),
        )
    ).first()
    return {"are_friends": row is not None}

# Optional: A public endpoint for other services to verify a token
# This returns the username if valid, so other services don't need to share the SECRET_KEY.
@router.post("/verify")
def verify_token(token: str):
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"valid": True, "username": payload.get("sub")}