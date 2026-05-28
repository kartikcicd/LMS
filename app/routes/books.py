import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
from app import db
from app.models import Book

books_bp = Blueprint('books', __name__, url_prefix='/books')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_cover(file):
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        return filename
    return None


@books_bp.route('/')
@login_required
def index():
    query = request.args.get('q', '')
    genre_filter = request.args.get('genre', '')
    genres = [g[0] for g in db.session.query(Book.genre).filter(Book.genre != None).distinct().all()]

    books_q = Book.query
    if query:
        books_q = books_q.filter(
            (Book.title.ilike(f'%{query}%')) |
            (Book.author.ilike(f'%{query}%')) |
            (Book.genre.ilike(f'%{query}%')) |
            (Book.isbn.ilike(f'%{query}%'))
        )
    if genre_filter:
        books_q = books_q.filter(Book.genre == genre_filter)
    books = books_q.order_by(Book.added_date.desc()).all()
    return render_template('books/index.html', books=books, query=query,
                           genres=genres, genre_filter=genre_filter)


@books_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        genre = request.form.get('genre')
        isbn = request.form.get('isbn')
        copies = int(request.form.get('total_copies', 1))
        if isbn and Book.query.filter_by(isbn=isbn).first():
            flash('A book with this ISBN already exists.', 'warning')
            return redirect(url_for('books.add'))
        cover_filename = save_cover(request.files.get('cover_image'))
        book = Book(title=title, author=author, genre=genre, isbn=isbn,
                    total_copies=copies, available_copies=copies,
                    cover_image=cover_filename)
        db.session.add(book)
        db.session.commit()
        flash(f'"{title}" added successfully!', 'success')
        return redirect(url_for('books.index'))
    return render_template('books/add.html')


@books_bp.route('/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit(book_id):
    book = Book.query.get_or_404(book_id)
    if request.method == 'POST':
        issued = book.total_copies - book.available_copies
        book.title = request.form.get('title')
        book.author = request.form.get('author')
        book.genre = request.form.get('genre')
        book.isbn = request.form.get('isbn')
        new_total = int(request.form.get('total_copies', 1))
        book.total_copies = new_total
        book.available_copies = max(0, new_total - issued)
        new_cover = save_cover(request.files.get('cover_image'))
        if new_cover:
            book.cover_image = new_cover
        db.session.commit()
        flash('Book updated successfully!', 'success')
        return redirect(url_for('books.index'))
    return render_template('books/edit.html', book=book)


@books_bp.route('/delete/<int:book_id>', methods=['POST'])
@login_required
def delete(book_id):
    book = Book.query.get_or_404(book_id)
    if book.available_copies < book.total_copies:
        flash('Cannot delete — some copies are currently issued.', 'danger')
        return redirect(url_for('books.index'))
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted.', 'info')
    return redirect(url_for('books.index'))

