"""
Restaurant Booking System
A clean and user-friendly Flask application for restaurant reservations.
"""

from datetime import datetime, date, time
from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DateField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bookings.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Restaurant settings
MAX_TABLES = 10          # Total tables in the restaurant
OPENING_HOUR = 11        # 11:00 AM
CLOSING_HOUR = 22        # 10:00 PM
MAX_GUESTS_PER_BOOKING = 10


# ---------------------------------------------------------------------------
# Database model
# ---------------------------------------------------------------------------
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    booking_time = db.Column(db.String(5), nullable=False)  # "HH:MM"
    guests = db.Column(db.Integer, nullable=False)
    special_requests = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Booking {self.name} - {self.booking_date} {self.booking_time}>"


# ---------------------------------------------------------------------------
# Booking form
# ---------------------------------------------------------------------------
class BookingForm(FlaskForm):
    name = StringField(
        'Full Name',
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"placeholder": "John Doe", "class": "form-input"}
    )
    email = StringField(
        'Email Address',
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "john@example.com", "class": "form-input"}
    )
    phone = StringField(
        'Phone Number',
        validators=[DataRequired(), Length(min=7, max=20)],
        render_kw={"placeholder": "+1 555 123 4567", "class": "form-input"}
    )
    booking_date = DateField(
        'Booking Date',
        validators=[DataRequired()],
        render_kw={"class": "form-input"}
    )
    booking_time = SelectField(
        'Booking Time',
        choices=[],
        validators=[DataRequired()],
        render_kw={"class": "form-input"}
    )
    guests = IntegerField(
        'Number of Guests',
        validators=[DataRequired(), NumberRange(min=1, max=MAX_GUESTS_PER_BOOKING)],
        render_kw={"placeholder": "2", "class": "form-input"}
    )
    special_requests = TextAreaField(
        'Special Requests (optional)',
        validators=[Length(max=500)],
        render_kw={"placeholder": "Window seat, birthday cake, allergies...", "class": "form-input", "rows": 3}
    )
    submit = SubmitField('Book Table', render_kw={"class": "btn-primary"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.booking_time.choices = [
            (f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}")
            for h in range(OPENING_HOUR, CLOSING_HOUR)
            for m in (0, 30)
        ]

    def validate_booking_date(self, field):
        if field.data < date.today():
            raise ValidationError('Booking date cannot be in the past.')

    def validate_booking_time(self, field):
        if self.booking_date.data == date.today():
            now = datetime.now()
            booking_hour, booking_minute = map(int, field.data.split(':'))
            if (booking_hour, booking_minute) <= (now.hour, now.minute):
                raise ValidationError('Please select a future time for today.')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def available_tables(booking_date, booking_time):
    """Return number of free tables at a given date/time."""
    booked = Booking.query.filter_by(
        booking_date=booking_date, booking_time=booking_time
    ).count()
    return MAX_TABLES - booked


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    form = BookingForm()
    if form.validate_on_submit():
        remaining = available_tables(form.booking_date.data, form.booking_time.data)
        if remaining <= 0:
            flash('Sorry, that time slot is fully booked. Please choose another time.', 'error')
        else:
            booking = Booking(
                name=form.name.data.strip(),
                email=form.email.data.strip(),
                phone=form.phone.data.strip(),
                booking_date=form.booking_date.data,
                booking_time=form.booking_time.data,
                guests=form.guests.data,
                special_requests=form.special_requests.data.strip() if form.special_requests.data else None,
            )
            db.session.add(booking)
            db.session.commit()
            flash(f'✅ Table booked successfully for {booking.name}! '
                  f'Confirmation will be sent to {booking.email}.', 'success')
            return redirect(url_for('confirmation', booking_id=booking.id))

    return render_template_string(INDEX_TEMPLATE, form=form)


@app.route('/confirmation/<int:booking_id>')
def confirmation(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    return render_template_string(CONFIRMATION_TEMPLATE, booking=booking)


@app.route('/bookings')
def bookings_list():
    all_bookings = Booking.query.order_by(
        Booking.booking_date.desc(), Booking.booking_time
    ).all()
    return render_template_string(BOOKINGS_TEMPLATE, bookings=all_bookings)


@app.route('/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    name = booking.name
    db.session.delete(booking)
    db.session.commit()
    flash(f'Booking for {name} has been cancelled.', 'success')
    return redirect(url_for('bookings_list'))


# ---------------------------------------------------------------------------
# Templates (inline for single-file convenience)
# ---------------------------------------------------------------------------
BASE_STYLE = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
    color: #333;
  }
  .container { max-width: 720px; margin: 0 auto; }
  .card {
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.15);
    padding: 40px;
    margin-bottom: 20px;
  }
  h1 { color: #4a3f8f; margin-bottom: 8px; font-size: 28px; }
  h2 { color: #4a3f8f; margin-bottom: 20px; font-size: 22px; }
  .subtitle { color: #666; margin-bottom: 30px; font-size: 15px; }
  .form-group { margin-bottom: 20px; }
  label {
    display: block;
    font-weight: 600;
    margin-bottom: 8px;
    color: #444;
    font-size: 14px;
  }
  .form-input {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 15px;
    font-family: inherit;
    transition: border-color 0.2s;
  }
  .form-input:focus {
    outline: none;
    border-color: #667eea;
  }
  .btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    padding: 14px 28px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    width: 100%;
    transition: transform 0.2s, box-shadow 0.2s;
  }
  .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
  }
  .btn-secondary {
    display: inline-block;
    background: #f0f0f5;
    color: #4a3f8f;
    padding: 10px 20px;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 600;
    font-size: 14px;
    margin-top: 10px;
    border: none;
    cursor: pointer;
  }
  .btn-danger {
    background: #ff4757;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
  }
  .flash {
    padding: 14px 20px;
    border-radius: 8px;
    margin-bottom: 20px;
    font-weight: 500;
  }
  .flash.success { background: #d4edda; color: #155724; border-left: 4px solid #28a745; }
  .flash.error { background: #f8d7da; color: #721c24; border-left: 4px solid #dc3545; }
  .errors { color: #dc3545; font-size: 13px; margin-top: 6px; }
  .booking-item {
    background: #f8f9ff;
    border-left: 4px solid #667eea;
    padding: 18px 20px;
    border-radius: 8px;
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }
  .booking-info strong { color: #4a3f8f; display: block; margin-bottom: 4px; }
  .booking-info span { color: #666; font-size: 14px; display: block; margin: 2px 0; }
  .empty { text-align: center; color: #999; padding: 40px 20px; font-style: italic; }
  .confirmation-icon { font-size: 60px; text-align: center; margin-bottom: 10px; }
  .details { background: #f8f9ff; border-radius: 10px; padding: 20px; margin: 20px 0; }
  .detail-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e8e8f0; }
  .detail-row:last-child { border-bottom: none; }
  .detail-label { color: #666; font-weight: 500; }
  .detail-value { color: #333; font-weight: 600; }
  .nav-link { color: #4a3f8f; text-decoration: none; font-weight: 600; font-size: 14px; }
</style>
"""

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Book a Table — The Purple Fig</title>
    """ + BASE_STYLE + """
</head>
<body>
<div class="container">
    <div class="card">
        <h1>🍽️ The Purple Fig</h1>
        <p class="subtitle">Reserve your table in just a few clicks.</p>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <form method="POST" novalidate>
            {{ form.hidden_tag() }}

            <div class="form-group">
                {{ form.name.label }}
                {{ form.name }}
                {% for e in form.name.errors %}<div class="errors">{{ e }}</div>{% endfor %}
            </div>

            <div class="form-group">
                {{ form.email.label }}
                {{ form.email }}
                {% for e in form.email.errors %}<div class="errors">{{ e }}</div>{% endfor %}
            </div>

            <div class="form-group">
                {{ form.phone.label }}
                {{ form.phone }}
                {% for e in form.phone.errors %}<div class="errors">{{ e }}</div>{% endfor %}
            </div>

            <div class="form-group">
                {{ form.booking_date.label }}
                {{ form.booking_date }}
                {% for e in form.booking_date.errors %}<div class="errors">{{ e }}</div>{% endfor %}
            </div>

            <div class="form-group">
                {{ form.booking_time.label }}
                {{ form.booking_time }}
                {% for e in form.booking_time.errors %}<div class="errors">{{ e }}</div>{% endfor %}
            </div>

            <div class="form-group">
                {{ form.guests.label }}
                {{ form.guests }}
                {% for e in form.guests.errors %}<div class="errors">{{ e }}</div>{% endfor %}
            </div>

            <div class="form-group">
                {{ form.special_requests.label }}
                {{ form.special_requests }}
                {% for e in form.special_requests.errors %}<div class="errors">{{ e }}</div>{% endfor %}
            </div>

            {{ form.submit }}
        </form>
    </div>
    <div style="text-align:center;">
        <a class="nav-link" href="{{ url_for('bookings_list') }}">View all bookings →</a>
    </div>
</div>
</body>
</html>
"""

CONFIRMATION_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Booking Confirmed — The Purple Fig</title>
    """ + BASE_STYLE + """
</head>
<body>
<div class="container">
    <div class="card">
        <div class="confirmation-icon">🎉</div>
        <h1 style="text-align:center;">Booking Confirmed!</h1>
        <p class="subtitle" style="text-align:center;">
            Thank you, {{ booking.name }}. We look forward to seeing you.
        </p>

        <div class="details">
            <div class="detail-row">
                <span class="detail-label">Confirmation #</span>
                <span class="detail-value">#{{ '%05d' % booking.id }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Date</span>
                <span class="detail-value">{{ booking.booking_date.strftime('%A, %B %d, %Y') }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Time</span>
                <span class="detail-value">{{ booking.booking_time }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Guests</span>
                <span class="detail-value">{{ booking.guests }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Email</span>
                <span class="detail-value">{{ booking.email }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Phone</span>
                <span class="detail-value">{{ booking.phone }}</span>
            </div>
            {% if booking.special_requests %}
            <div class="detail-row">
                <span class="detail-label">Special Requests</span>
                <span class="detail-value">{{ booking.special_requests }}</span>
            </div>
            {% endif %}
        </div>

        <a class="btn-secondary" href="{{ url_for('index') }}">← Make another booking</a>
        <a class="btn-secondary" href="{{ url_for('bookings_list') }}">View all bookings</a>
    </div>
</div>
</body>
</html>
"""

BOOKINGS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>All Bookings — The Purple Fig</title>
    """ + BASE_STYLE + """
</head>
<body>
<div class="container">
    <div class="card">
        <h2>📋 All Reservations</h2>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        {% if bookings %}
            {% for b in bookings %}
            <div class="booking-item">
                <div class="booking-info">
                    <strong>{{ b.name }} · {{ b.guests }} guest{{ 's' if b.guests != 1 else '' }}</strong>
                    <span>📅 {{ b.booking_date.strftime('%a, %b %d, %Y') }} at {{ b.booking_time }}</span>
                    <span>📧 {{ b.email }} · 📞 {{ b.phone }}</span>
                    {% if b.special_requests %}<span>📝 {{ b.special_requests }}</span>{% endif %}
                </div>
                <form method="POST" action="{{ url_for('cancel_booking', booking_id=b.id) }}"
                      onsubmit="return confirm('Cancel this booking?');">
                    <button type="submit" class="btn-danger">Cancel</button>
                </form>
            </div>
            {% endfor %}
        {% else %}
            <p class="empty">No reservations yet. Be the first to book a table!</p>
        {% endif %}

        <a class="btn-secondary" href="{{ url_for('index') }}">← New Booking</a>
    </div>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
