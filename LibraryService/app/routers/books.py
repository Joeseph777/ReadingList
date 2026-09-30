from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
from ..database import get_db
from ..models import Book
from ..schemas import BookCreate, BookUpdate, BookOut, BookProgressUpdate, BookRatingUpdate, BookCommentUpdate
from ..auth_dep import get_current_user
from ..config import settings

router = APIRouter(prefix="/books", tags=["Books"])

@router.post("/", response_model=BookOut)
def create_book(book: BookCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    db_book = Book(**book.model_dump(), user_id=user_id)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@router.get("/", response_model=List[BookOut])
def list_books(
    status: Optional[str] = Query(None, pattern="^(unread|progress|completed)$"),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    query = db.query(Book).filter(Book.user_id == user_id)
    if search:
        query = query.filter((Book.title.contains(search)) | (Book.author.contains(search)))
    books = query.all()
    
    # Filter by status after computing reading level
    if status == "unread":
        books = [b for b in books if b.pages_read == 0]
    elif status == "progress":
        books = [b for b in books if 0 < b.pages_read < b.pages]
    elif status == "completed":
        books = [b for b in books if b.pages_read >= b.pages]
    return books

@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@router.get("/friend/{friend_id}", response_model=List[BookOut])
def list_friend_books(friend_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    if friend_id == user_id:
        raise HTTPException(status_code=400, detail="That's your own list — use GET /books/ instead")
    try:
        resp = httpx.get(
            f"{settings.AUTH_SERVICE_URL}/auth/internal/are-friends",
            params={"user_a": user_id, "user_b": friend_id},
            timeout=5.0,
        )
        resp.raise_for_status()
        are_friends = resp.json().get("are_friends", False)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Couldn't reach AuthService to verify friendship")

    if not are_friends:
        raise HTTPException(status_code=403, detail="You can only view a friend's reading list")

    return db.query(Book).filter(Book.user_id == friend_id).all()

@router.put("/{book_id}", response_model=BookOut)
def update_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    for key, value in book_update.model_dump(exclude_unset=True).items():
        setattr(book, key, value)
    db.commit()
    db.refresh(book)
    return book

@router.delete("/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return {"detail": "Book deleted"}

@router.patch("/{book_id}/progress")
def update_progress(book_id: int, progress: BookProgressUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if progress.pages_read < 0 or progress.pages_read > book.pages:
        raise HTTPException(status_code=400, detail="Pages read out of range")
    book.pages_read = progress.pages_read
    db.commit()
    db.refresh(book)
    return {"detail": "Progress updated", "reading_level": (book.pages_read / book.pages) * 100}

@router.patch("/{book_id}/rating", response_model=BookOut)
def update_rating(book_id: int, rating: BookRatingUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if not (0 <= rating.rating <= 10):
        raise HTTPException(status_code=400, detail="Rating must be between 0 and 10")
    book.rating = rating.rating
    db.commit()
    db.refresh(book)
    return book

@router.patch("/{book_id}/comments", response_model=BookOut)
def update_comments(book_id: int, comment: BookCommentUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    book.comments = comment.comments
    db.commit()
    db.refresh(book)
    return book

# Internal, unauthenticated cleanup used by AuthService (trusted local network) when an
# admin deletes a user account — wipes that user's books along with it.
@router.delete("/internal/by-user/{user_id}")
def delete_books_by_user(user_id: int, db: Session = Depends(get_db)):
    deleted = db.query(Book).filter(Book.user_id == user_id).delete(synchronize_session=False)
    db.commit()
    return {"detail": f"Deleted {deleted} book(s) for user {user_id}"}