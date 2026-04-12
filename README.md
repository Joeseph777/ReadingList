# 📚 Personal Reading List Manager

A personal reading tracker built in Python — available both as a **command-line app** and a **graphical desktop interface (GUI)**. Track what you've read, how far along you are, your ratings, and your thoughts on each book.

---

## Features

- Add books with title, author, year, page count, and original language
- Track reading progress by pages read (stored as a percentage)
- Rate books on a scale of 0–10
- Write and store personal comments/reviews
- Filter books by status: Unread, In Progress, or Completed
- Search by title, author, or language
- Sort by reading level, author, title, or publication year
- View reading statistics (totals, average rating, total pages)
- Persistent storage via a local JSON file (`reading_list.json`)
- Duplicate detection (case-insensitive title + author check)

---

## Project Structure

```
ReadingList/
├── ReadingList.py        # Core logic: Book and ReadingList classes + CLI interface
├── ReadingListGUI.py     # Tkinter-based graphical interface
├── reading_list.json     # Saved reading data (auto-generated on first save)
└── README.md
```

---

## Requirements

- Python 3.7+
- `tkinter` (included with standard Python on Windows and most Linux distros)
- No external packages required

---

## How to Run

### Command-Line Interface
```bash
python ReadingList.py
```
Navigate using the numbered menu to add books, update progress, rate, comment, sort, and save.

### Graphical Interface (GUI)
```bash
python ReadingListGUI.py
```
Opens a desktop window with buttons and forms for all the same features.

---

## Data Format

Books are saved to `reading_list.json` in the following format:

```json
{
  "title": "Animal Farm",
  "author": "George Orwell",
  "year": 1945,
  "nb_pages": 71,
  "OriginalLanguage": "English",
  "ReadingLevel": 100.0,
  "Rating": 9.5,
  "Comments": "..."
}
```

---

## Author

**Youssef Baratli**  
Engineering Student — Institut Supérieur d'Informatique, Tunis  
Co-diplomation — Université Sorbonne Paris Nord (USPN)
