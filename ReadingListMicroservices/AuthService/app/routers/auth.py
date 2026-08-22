from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import timedelta
import httpx

from typing import List, Optional

from ..database import get_db
from ..models import User, Friendship
from ..schemas import UserCreate, UserLogin, UserOut, Token, FriendsList, FriendUser, RespondRequest
from ..auth import verify_password, get_password_hash, create_access_token
from ..dependencies import get_current_user, get_current_admin
from ..config import settings
from ..rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Both endpoints below take `request: Request` as the first parameter — slowapi
# requires this to identify the caller's IP, even though the route body never
# uses it directly.

@router.post("/register", response_model=UserOut)
@limiter.limit("10/minute")
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    # Check if username or email already exists
    existing_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    is_admin = False
    if user.admin_code:
        if user.admin_code != settings.ADMIN_ACCESS_CODE:
            raise HTTPException(status_code=403, detail="Invalid admin code")
        is_admin = True

    hashed = get_password_hash(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed, is_admin=is_admin)
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

# Admin-only: full user list with management controls in the web app.
@router.get("/users", response_model=List[UserOut])
def list_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()

# Any logged-in user can search/browse other users — this is how you find people to
# friend. Deliberately lighter than /users: no admin gate, but capped result size.
@router.get("/search", response_model=List[UserOut])
def search_users(q: str = "", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(User).filter(User.id != current_user.id)
    if q.strip():
        query = query.filter(User.username.ilike(f"%{q.strip()}%"))
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
        entry = FriendUser(friendship_id=f.id, id=other.id, username=other.username, email=other.email)
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