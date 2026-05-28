import csv
import io
from flask import Blueprint, Response
from flask_login import login_required, current_user
from app.models import Book, Member, Transaction
from functools import wraps

# Role-based access control decorator
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or getattr(current_user, 'role', None) != role:
                from flask import abort
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def make_csv(headers, rows, filename):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@reports_bp.route('/books')
@login_required
@role_required('admin')
def export_books():
    books = Book.query.all()
    headers = ['ID', 'Title', 'Author', 'Genre', 'ISBN', 'Total Copies', 'Available']
    rows = [[b.id, b.title, b.author, b.genre or '', b.isbn or '',
             b.total_copies, b.available_copies] for b in books]
    return make_csv(headers, rows, 'books.csv')


@reports_bp.route('/members')
@login_required
@role_required('admin')
def export_members():
    members = Member.query.all()
    headers = ['ID', 'Name', 'Email', 'Phone', 'Joined', 'Active', 'Borrow Limit', 'Total Fine (₹)']
    rows = [[m.id, m.name, m.email, m.phone or '',
             m.membership_date.strftime('%d %b %Y'),
             'Yes' if m.is_active else 'No',
             m.max_books, f'{m.total_fine():.2f}'] for m in members]
    return make_csv(headers, rows, 'members.csv')


@reports_bp.route('/transactions')
@login_required
@role_required('admin')
def export_transactions():
    transactions = Transaction.query.order_by(Transaction.issue_date.desc()).all()
    headers = ['ID', 'Book', 'Member', 'Issue Date', 'Due Date', 'Return Date', 'Status', 'Fine (₹)']
    rows = [[
        t.id, t.book.title, t.member.name,
        t.issue_date.strftime('%d %b %Y'),
        t.due_date.strftime('%d %b %Y'),
        t.return_date.strftime('%d %b %Y') if t.return_date else '',
        t.status,
        f'{t.fine():.2f}'
    ] for t in transactions]
    return make_csv(headers, rows, 'transactions.csv')
