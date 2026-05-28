from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import Book, Member, Reservation

reservations_bp = Blueprint('reservations', __name__, url_prefix='/reservations')


@reservations_bp.route('/')
@login_required
def index():
    reservations = Reservation.query.order_by(Reservation.reserved_date.desc()).all()
    return render_template('reservations/index.html', reservations=reservations)


@reservations_bp.route('/reserve', methods=['GET', 'POST'])
@login_required
def reserve():
    # Show only books with 0 available copies (unavailable ones worth reserving)
    books = Book.query.filter(Book.available_copies == 0).all()
    members = Member.query.filter_by(is_active=True).all()
    if request.method == 'POST':
        book_id = int(request.form.get('book_id'))
        member_id = int(request.form.get('member_id'))
        # Prevent duplicate pending reservations
        existing = Reservation.query.filter_by(
            book_id=book_id, member_id=member_id, status='pending'
        ).first()
        if existing:
            flash('This member already has a pending reservation for this book.', 'warning')
            return redirect(url_for('reservations.reserve'))
        reservation = Reservation(book_id=book_id, member_id=member_id)
        db.session.add(reservation)
        db.session.commit()
        book = Book.query.get(book_id)
        member = Member.query.get(member_id)
        flash(f'Reservation placed for "{book.title}" by {member.name}.', 'success')
        return redirect(url_for('reservations.index'))
    return render_template('reservations/reserve.html', books=books, members=members)


@reservations_bp.route('/cancel/<int:reservation_id>', methods=['POST'])
@login_required
def cancel(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    reservation.status = 'cancelled'
    db.session.commit()
    flash('Reservation cancelled.', 'info')
    return redirect(url_for('reservations.index'))
