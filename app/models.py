from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import check_password_hash
from app import db, login_manager

FINE_PER_DAY = 2.0  # ₹ per day


class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50))
    isbn = db.Column(db.String(20), unique=True)
    total_copies = db.Column(db.Integer, default=1)
    available_copies = db.Column(db.Integer, default=1)
    cover_image = db.Column(db.String(200), nullable=True)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    transactions = db.relationship('Transaction', backref='book', lazy=True)
    reservations = db.relationship('Reservation', backref='book', lazy=True)

    def __repr__(self):
        return f'<Book {self.title}>'


class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    membership_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    max_books = db.Column(db.Integer, default=3)  # M2: borrowing limit
    transactions = db.relationship('Transaction', backref='member', lazy=True)
    reservations = db.relationship('Reservation', backref='member', lazy=True)

    def currently_issued_count(self):
        return Transaction.query.filter_by(member_id=self.id).filter(
            Transaction.status.in_(['issued', 'overdue'])
        ).count()

    def total_fine(self):
        return sum(t.fine() for t in self.transactions if t.status in ('overdue', 'returned'))

    def __repr__(self):
        return f'<Member {self.name}>'


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='issued')  # issued / returned / overdue

    def is_overdue(self):
        if self.status in ('issued', 'overdue') and datetime.utcnow() > self.due_date:
            return True
        return False

    def fine(self):
        """Calculate fine in ₹ based on overdue days."""
        ref_date = self.return_date if self.return_date else datetime.utcnow()
        if ref_date > self.due_date:
            overdue_days = (ref_date - self.due_date).days
            return round(overdue_days * FINE_PER_DAY, 2)
        return 0.0

    def overdue_days(self):
        ref_date = self.return_date if self.return_date else datetime.utcnow()
        if ref_date > self.due_date:
            return (ref_date - self.due_date).days
        return 0

    def __repr__(self):
        return f'<Transaction {self.id} - {self.status}>'


class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    reserved_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending / fulfilled / cancelled

    def __repr__(self):
        return f'<Reservation {self.id} - {self.status}>'


class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='admin')  # 'admin' or 'staff'

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))