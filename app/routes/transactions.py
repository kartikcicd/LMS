from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import Book, Member, Transaction, Reservation

transactions_bp = Blueprint('transactions', __name__, url_prefix='/transactions')


@transactions_bp.route('/')
@login_required
def index():
    transactions = Transaction.query.order_by(Transaction.issue_date.desc()).all()
    for t in transactions:
        if t.is_overdue():
            t.status = 'overdue'
    db.session.commit()
    return render_template('transactions/index.html', transactions=transactions)


@transactions_bp.route('/issue', methods=['GET', 'POST'])
@login_required
def issue():
    books = Book.query.filter(Book.available_copies > 0).all()
    members = Member.query.filter_by(is_active=True).all()
    if request.method == 'POST':
        book_id = int(request.form.get('book_id'))
        member_id = int(request.form.get('member_id'))
        days = int(request.form.get('loan_days', 14))
        book = Book.query.get_or_404(book_id)
        member = Member.query.get_or_404(member_id)

        if book.available_copies < 1:
            flash('No copies available for this book.', 'danger')
            return redirect(url_for('transactions.issue'))

        # M2: Enforce borrowing limit
        if member.currently_issued_count() >= member.max_books:
            flash(f'{member.name} has reached their borrowing limit of {member.max_books} book(s).', 'danger')
            return redirect(url_for('transactions.issue'))

        due_date = datetime.utcnow() + timedelta(days=days)
        transaction = Transaction(book_id=book_id, member_id=member_id, due_date=due_date)
        book.available_copies -= 1

        # Fulfil any pending reservation for this member+book
        reservation = Reservation.query.filter_by(
            book_id=book_id, member_id=member_id, status='pending'
        ).first()
        if reservation:
            reservation.status = 'fulfilled'

        db.session.add(transaction)
        db.session.commit()
        flash(f'"{book.title}" issued to {member.name}. Due: {due_date.strftime("%d %b %Y")}', 'success')
        return redirect(url_for('transactions.index'))
    return render_template('transactions/issue.html', books=books, members=members)


@transactions_bp.route('/return/<int:transaction_id>', methods=['POST'])
@login_required
def return_book(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.status == 'returned':
        flash('This book has already been returned.', 'warning')
        return redirect(url_for('transactions.index'))
    transaction.return_date = datetime.utcnow()
    transaction.status = 'returned'
    transaction.book.available_copies += 1
    db.session.commit()
    fine = transaction.fine()
    if fine > 0:
        flash(f'"{transaction.book.title}" returned. Fine collected: ₹{fine:.2f}', 'warning')
    else:
        flash(f'"{transaction.book.title}" returned successfully!', 'success')
    return redirect(url_for('transactions.index'))

