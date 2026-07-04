import os
import json
from datetime import datetime

# Resolve save file path relative to this script, so it works from any working directory
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SAVE_PATH = os.path.join(_SCRIPT_DIR, "reading_list.json")

class Book:
    def __init__(self, title, author, year, nb_pages, OriginalLanguage, ReadingLevel=0, Rating=0, Comments="", Genre="", Summary=""):
        self.title = title
        self.author = author
        self.year = year
        self.nb_pages = nb_pages
        self.OriginalLanguage = OriginalLanguage
        self.Rating = Rating
        self.ReadingLevel = ReadingLevel
        self.Comments = Comments
        

    def __repr__(self):        
        return f"Book(title='{self.title}', author='{self.author}', year={self.year}, nb_pages={self.nb_pages}, OriginalLanguage='{self.OriginalLanguage}', ReadingLevel={self.ReadingLevel:.1f}%, Rating={self.Rating}), Genre='{self.Genre}'"
    
    def update_reading_level(self, pages_read):
        if self.nb_pages == 0:
            self.ReadingLevel = 0
        else:
            self.ReadingLevel = (pages_read / self.nb_pages) * 100
    
    def update_rating(self, new_rating):
        if 0 <= new_rating <= 10:
            self.Rating = new_rating
        else:
            raise ValueError("Rating must be between 0 and 10.")    
    
    def add_comment(self, comment):
        self.Comments += comment + "\n"
    
    def to_dict(self):
        return {
            'title': self.title,
            'author': self.author,
            'year': self.year,
            'nb_pages': self.nb_pages,
            'OriginalLanguage': self.OriginalLanguage,
            'ReadingLevel': self.ReadingLevel,
            'Rating': self.Rating,
            'Comments': self.Comments,
            
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            data['title'],
            data['author'],
            data['year'],
            data['nb_pages'],
            data['OriginalLanguage'],
            data['ReadingLevel'],
            data['Rating'],
            data['Comments'],
            
        )

class ReadingList:
    def __init__(self, BookList=None):
        self.books = BookList if BookList else []
    
    def _is_duplicate(self, book):
        """Return True if a book with the same title+author already exists (case-insensitive)."""
        key = (book.title.strip().lower(), book.author.strip().lower())
        return any(
            (b.title.strip().lower(), b.author.strip().lower()) == key
            for b in self.books
        )

    def add_book(self, book):
        if self._is_duplicate(book):
            raise ValueError(
                f"'{book.title}' by {book.author} is already in your reading list."
            )
        self.books.append(book)
        
    
    def remove_book(self, book):
        self.books.remove(book)
        
    
    def get_books_by_author(self, author):
        return [book for book in self.books if book.author.lower() == author.lower()]
    
    def SortBooksByReadingLevel(self):
        self.books.sort(key=lambda book: book.ReadingLevel, reverse=True)

    def SortBooksByRating(self):
        self.books.sort(key=lambda book: book.Rating, reverse=True)
    
    def SortBooksByAuthor(self):
        self.books.sort(key=lambda book: book.author.lower())
        
    
    def SortBooksByTitle(self):
        self.books.sort(key=lambda book: book.title.lower())
        
    def SortBooksByOriginalLanguage(self):
        self.books.sort(key=lambda book: book.OriginalLanguage.lower())

    def SortBooksByPages(self):
        self.books.sort(key=lambda book: book.nb_pages, reverse=False)

    def SortBooksByComments(self):
        #This is an exception catch it should not be used for sorting but it is here for the sake of completeness
        self.books.sort(key=lambda book: book.Comments, reverse=True)
    def SortBooksByYear(self):
        self.books.sort(key=lambda book: book.year, reverse=True)
    def get_unread_books(self):
        return [book for book in self.books if book.ReadingLevel == 0]
    
    def get_completed_books(self):
        return [book for book in self.books if book.ReadingLevel >= 100]
    
    def get_in_progress_books(self):
        return [book for book in self.books if 0 < book.ReadingLevel < 100]
    
    def get_statistics(self):
        total_books = len(self.books)
        if total_books == 0:
            return "No books in your list yet!"
        
        completed = len(self.get_completed_books())
        in_progress = len(self.get_in_progress_books())
        unread = len(self.get_unread_books())
        
        avg_rating = sum(book.Rating for book in self.books if book.Rating > 0) / len([b for b in self.books if b.Rating > 0]) if any(b.Rating > 0 for b in self.books) else 0
        
        total_pages = sum(book.nb_pages for book in self.books)
        total_pages_read = sum((book.nb_pages) for book in self.get_completed_books()) + sum((book.nb_pages) for book in self.get_in_progress_books())
        
        return f"""
📊 READING LIST STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━
Total Books: {total_books}
├─ Completed: {completed}
├─ In Progress: {in_progress}
└─ Unread: {unread}

Average Rating: {avg_rating:.1f}/10
Total Pages: {total_pages}
Total Pages Read: {total_pages_read}
        """
    
    def search_books(self, query):
        query = query.lower()
        return [book for book in self.books 
                if query in book.title.lower() 
                or query in book.author.lower()
                or query in book.OriginalLanguage.lower()]
    
    def save_to_file(self, filename=None):
        filename = filename or DEFAULT_SAVE_PATH
        data = [book.to_dict() for book in self.books]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return (f"💾 Reading list saved to {filename}")
    
    def load_from_file(self, filename=None):
        filename = filename or DEFAULT_SAVE_PATH
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.books = [Book.from_dict(book_data) for book_data in data]
            return f"📂 Loaded {len(self.books)} books from {filename}"
        except FileNotFoundError:
            return "📂 No existing file found. Starting with empty list."
        except json.JSONDecodeError:
            return "⚠️  Error reading file. Starting with empty list."
    
    def __repr__(self):
        return f"ReadingList(books={self.books})"

def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print app header"""
    print("""
╔══════════════════════════════════════╗
║      📚 PERSONAL READING LIST       ║
║         Track Your Reading           ║
╚══════════════════════════════════════╝
    """)

def add_book_interactive(reading_list):
    """Interactive function to add a new book"""
    print("\n➕ ADD NEW BOOK")
    print("-" * 30)
    
    title = input("Title: ").strip()
    if not title:
        print("❌ Title cannot be empty!")
        return
    
    author = input("Author: ").strip()
    if not author:
        print("❌ Author cannot be empty!")
        return
    
    try:
        year = int(input("Publication Year: "))
        nb_pages = int(input("Number of Pages: "))
        if nb_pages <= 0:
            print("❌ Pages must be positive!")
            return
    except ValueError:
        print("❌ Please enter valid numbers!")
        return
    
    language = input("Original Language: ").strip()
    if not language:
        language = "Unknown"
    
    book = Book(title, author, year, nb_pages, language)
    reading_list.add_book(book)
    
    # Ask if they want to add more details
    if input("\nAdd reading progress now? (y/n): ").lower() == 'y':
        update_progress_interactive(reading_list, book)
    
    input("\nPress Enter to continue...")

def update_progress_interactive(reading_list, book=None):
    """Update reading progress for a book"""
    if not book:
        if not reading_list.books:
            print("📭 No books in your list!")
            input("Press Enter to continue...")
            return
        
        print("\n📖 SELECT A BOOK")
        for i, b in enumerate(reading_list.books, 1):
            status = "✅" if b.ReadingLevel >= 100 else "📖" if b.ReadingLevel > 0 else "⏳"
            print(f"{i}. {status} {b.title} by {b.author} ({b.ReadingLevel:.1f}%)")
        
        try:
            choice = int(input("\nSelect book number: ")) - 1
            if 0 <= choice < len(reading_list.books):
                book = reading_list.books[choice]
            else:
                print("❌ Invalid selection!")
                return
        except ValueError:
            print("❌ Please enter a number!")
            return
    
    print(f"\nUpdating progress for: {book.title}")
    try:
        pages = int(input(f"Pages read so far (max {book.nb_pages}): "))
        if 0 <= pages <= book.nb_pages:
            book.update_reading_level(pages)
            print(f"✅ Progress updated to {book.ReadingLevel:.1f}%")
            
            if book.ReadingLevel >= 100:
                print("🎉 Congratulations! You've completed this book!")
                
                if book.Rating == 0 and input("Would you like to rate it? (y/n): ").lower() == 'y':
                    try:
                        rating = float(input("Rating (0-10): "))
                        book.update_rating(rating)
                        print(f"⭐ Rating saved: {rating}/10")
                    except ValueError as e:
                        print(f"⚠️  {e}")
        else:
            print(f"❌ Pages must be between 0 and {book.nb_pages}")
    except ValueError:
        print("❌ Please enter a valid number!")
    
    input("\nPress Enter to continue...")

def view_books(reading_list):
    """Display books with filtering options"""
    if not reading_list.books:
        print("\n📭 Your reading list is empty!")
        input("Press Enter to continue...")
        return
    
    while True:
        clear_screen()
        print_header()
        print("\n🔍 VIEW BOOKS")
        print("1. All Books")
        print("2. Unread Books")
        print("3. Books in Progress")
        print("4. Completed Books")
        print("5. Search Books")
        print("6. Back to Main Menu")
        
        choice = input("\nSelect option: ")
        
        books_to_show = []
        title = ""
        
        if choice == '1':
            books_to_show = reading_list.books
            title = "ALL BOOKS"
        elif choice == '2':
            books_to_show = reading_list.get_unread_books()
            title = "UNREAD BOOKS"
        elif choice == '3':
            books_to_show = reading_list.get_in_progress_books()
            title = "BOOKS IN PROGRESS"
        elif choice == '4':
            books_to_show = reading_list.get_completed_books()
            title = "COMPLETED BOOKS"
        elif choice == '5':
            query = input("Enter search term: ").strip()
            books_to_show = reading_list.search_books(query)
            title = f"SEARCH RESULTS: '{query}'"
        elif choice == '6':
            break
        else:
            continue
        
        clear_screen()
        print_header()
        print(f"\n{title}")
        print("=" * 50)
        
        if not books_to_show:
            print("No books found.")
        else:
            for i, book in enumerate(books_to_show, 1):
                status = "✅" if book.ReadingLevel >= 100 else "📖" if book.ReadingLevel > 0 else "⏳"
                print(f"\n{i}. {status} {book.title}")
                print(f"   Author: {book.author} ({book.year})")
                print(f"   Pages: {book.nb_pages} | Language: {book.OriginalLanguage}")
                print(f"   Progress: {book.ReadingLevel:.1f}% | Rating: {book.Rating}/10")
                if book.Comments:
                    print(f"   Comments: {book.Comments.strip()}")
        
        input("\nPress Enter to continue...")

def main():
    """Main application loop"""
    reading_list = ReadingList()
    
    # Try to load existing data
    if os.path.exists(DEFAULT_SAVE_PATH):
        if input("Load existing reading list? (y/n): ").lower() == 'y':
            reading_list.load_from_file()
    
    while True:
        clear_screen()
        print_header()
        
        print("\nMAIN MENU")
        print("1. 📖 View My Books")
        print("2. ➕ Add New Book")
        print("3. 📊 Update Reading Progress")
        print("4. ⭐ Rate a Book")
        print("5. 💬 Add Comment to Book")
        print("6. 🗑️  Remove a Book")
        print("7. 📈 View Statistics")
        print("8. 🔄 Sort Books")
        print("9. 💾 Save & Exit")
        
        choice = input("\nSelect option: ")
        
        if choice == '1':
            view_books(reading_list)
        
        elif choice == '2':
            clear_screen()
            print_header()
            add_book_interactive(reading_list)
        
        elif choice == '3':
            clear_screen()
            print_header()
            update_progress_interactive(reading_list)
        
        elif choice == '4':
            clear_screen()
            print_header()
            if not reading_list.books:
                print("📭 No books in your list!")
                input("Press Enter to continue...")
                continue
            
            print("\n⭐ RATE A BOOK")
            for i, book in enumerate(reading_list.books, 1):
                print(f"{i}. {book.title} by {book.author} (Current: {book.Rating}/10)")
            
            try:
                choice = int(input("\nSelect book number: ")) - 1
                if 0 <= choice < len(reading_list.books):
                    book = reading_list.books[choice]
                    rating = float(input(f"Rating for '{book.title}' (0-10): "))
                    book.update_rating(rating)
                    print(f"✅ Rating updated to {rating}/10")
                else:
                    print("❌ Invalid selection!")
            except ValueError as e:
                print(f"❌ {e}")
            
            input("Press Enter to continue...")
        
        elif choice == '5':
            clear_screen()
            print_header()
            if not reading_list.books:
                print("📭 No books in your list!")
                input("Press Enter to continue...")
                continue
            
            print("\n💬 ADD COMMENT")
            for i, book in enumerate(reading_list.books, 1):
                print(f"{i}. {book.title} by {book.author}")
            
            try:
                choice = int(input("\nSelect book number: ")) - 1
                if 0 <= choice < len(reading_list.books):
                    book = reading_list.books[choice]
                    comment = input("Enter your comment: ")
                    book.add_comment(comment)
                    print("✅ Comment added!")
                else:
                    print("❌ Invalid selection!")
            except ValueError:
                print("❌ Please enter a number!")
            
            input("Press Enter to continue...")
        
        elif choice == '6':
            clear_screen()
            print_header()
            if not reading_list.books:
                print("📭 No books in your list!")
                input("Press Enter to continue...")
                continue
            
            print("\n🗑️  REMOVE A BOOK")
            for i, book in enumerate(reading_list.books, 1):
                print(f"{i}. {book.title} by {book.author}")
            
            try:
                choice = int(input("\nSelect book number to remove: ")) - 1
                if 0 <= choice < len(reading_list.books):
                    book = reading_list.books[choice]
                    if input(f"Are you sure you want to remove '{book.title}'? (y/n): ").lower() == 'y':
                        reading_list.remove_book(book)
                else:
                    print("❌ Invalid selection!")
            except ValueError:
                print("❌ Please enter a number!")
            
            input("Press Enter to continue...")
        
        elif choice == '7':
            clear_screen()
            print_header()
            print(reading_list.get_statistics())
            input("\nPress Enter to continue...")
        
        elif choice == '8':
            clear_screen()
            print_header()
            print("\n🔄 SORT BOOKS BY:")
            print("1. Reading Level")
            print("2. Author")
            print("3. Title")
            print("4. Year")
            
            sort_choice = input("\nSelect option: ")
            
            if sort_choice == '1':
                reading_list.SortBooksByReadingLevel()
            elif sort_choice == '2':
                reading_list.SortBooksByAuthor()
            elif sort_choice == '3':
                reading_list.SortBooksByTitle()
            elif sort_choice == '4':
                reading_list.SortBooksByYear()
            else:
                print("Invalid option!")
            
            input("Press Enter to continue...")
        
        elif choice == '9':
            reading_list.save_to_file()
            print("\n👋 Goodbye! Happy reading!")
            break

if __name__ == "__main__":
    main()