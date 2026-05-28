from datetime import datetime
from collections import defaultdict
from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Book, Member, Transaction

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    total_books = Book.query.count()
    total_members = Member.query.count()

    # Update overdue statuses
    from app import db
    for t in Transaction.query.filter(Transaction.status.in_(['issued'])).all():
        if t.is_overdue():
            t.status = 'overdue'
    db.session.commit()

    total_issued = Transaction.query.filter(Transaction.status.in_(['issued', 'overdue'])).count()
    total_overdue = Transaction.query.filter_by(status='overdue').count()
    overdue_list = Transaction.query.filter_by(status='overdue').all()
    recent_transactions = Transaction.query.order_by(Transaction.issue_date.desc()).limit(10).all()

    # A3: Books by genre for pie chart
    genre_data = defaultdict(int)
    for book in Book.query.all():
        genre_data[book.genre or 'Unknown'] += book.total_copies
    genre_labels = list(genre_data.keys())
    genre_values = list(genre_data.values())

    # A3: Monthly issues (last 6 months) for bar chart
    from sqlalchemy import extract
    now = datetime.utcnow()
    monthly_labels = []
    monthly_values = []
    for i in range(5, -1, -1):
        month = (now.month - i - 1) % 12 + 1
        year = now.year - ((now.month - i - 1) // 12)
        count = Transaction.query.filter(
            extract('month', Transaction.issue_date) == month,
            extract('year', Transaction.issue_date) == year
        ).count()
        monthly_labels.append(datetime(year, month, 1).strftime('%b %Y'))
        monthly_values.append(count)

    return render_template('dashboard.html',
        total_books=total_books,
        total_members=total_members,
        total_issued=total_issued,
        total_overdue=total_overdue,
        overdue_list=overdue_list,
        recent_transactions=recent_transactions,
        genre_labels=genre_labels,
        genre_values=genre_values,
        monthly_labels=monthly_labels,
        monthly_values=monthly_values,
        now=now
    )

