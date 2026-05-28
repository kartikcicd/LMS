from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import Member, Transaction, Reservation

members_bp = Blueprint('members', __name__, url_prefix='/members')


@members_bp.route('/')
@login_required
def index():
    query = request.args.get('q', '')
    if query:
        members = Member.query.filter(
            (Member.name.ilike(f'%{query}%')) |
            (Member.email.ilike(f'%{query}%')) |
            (Member.phone.ilike(f'%{query}%'))
        ).all()
    else:
        members = Member.query.order_by(Member.membership_date.desc()).all()
    return render_template('members/index.html', members=members, query=query)


@members_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        max_books = int(request.form.get('max_books', 3))
        if Member.query.filter_by(email=email).first():
            flash('A member with this email already exists.', 'warning')
            return redirect(url_for('members.add'))
        member = Member(name=name, email=email, phone=phone, max_books=max_books)
        db.session.add(member)
        db.session.commit()
        flash(f'Member "{name}" registered successfully!', 'success')
        return redirect(url_for('members.index'))
    return render_template('members/add.html')


@members_bp.route('/edit/<int:member_id>', methods=['GET', 'POST'])
@login_required
def edit(member_id):
    member = Member.query.get_or_404(member_id)
    if request.method == 'POST':
        member.name = request.form.get('name')
        member.email = request.form.get('email')
        member.phone = request.form.get('phone')
        member.max_books = int(request.form.get('max_books', 3))
        member.is_active = 'is_active' in request.form
        db.session.commit()
        flash('Member updated successfully!', 'success')
        return redirect(url_for('members.index'))
    return render_template('members/edit.html', member=member)


@members_bp.route('/profile/<int:member_id>')
@login_required
def profile(member_id):
    member = Member.query.get_or_404(member_id)
    transactions = Transaction.query.filter_by(member_id=member_id).order_by(Transaction.issue_date.desc()).all()
    reservations = Reservation.query.filter_by(member_id=member_id).order_by(Reservation.reserved_date.desc()).all()
    active_count = member.currently_issued_count()
    total_fine = member.total_fine()
    return render_template('members/profile.html', member=member,
                           transactions=transactions, reservations=reservations,
                           active_count=active_count, total_fine=total_fine)


@members_bp.route('/delete/<int:member_id>', methods=['POST'])
@login_required
def delete(member_id):
    member = Member.query.get_or_404(member_id)
    active_issues = [t for t in member.transactions if t.status in ('issued', 'overdue')]
    if active_issues:
        flash('Cannot delete — member has books currently issued.', 'danger')
        return redirect(url_for('members.index'))
    db.session.delete(member)
    db.session.commit()
    flash('Member removed.', 'info')
    return redirect(url_for('members.index'))

