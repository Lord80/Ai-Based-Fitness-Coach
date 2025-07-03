from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import date
import pickle
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os
from prophet import Prophet
import plotly.graph_objs as go
import plotly.offline as pyo

app = Flask(__name__)

load_dotenv()

# Mail config
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_DEFAULT_SENDER'] = 'atharvdivekar80@gmail.com'

mail = Mail(app)

app.secret_key = os.getenv('SECRET_KEY')

# MySQL config
app.config['MYSQL_HOST'] = os.getenv('DB_HOST')
app.config['MYSQL_USER'] = os.getenv('DB_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASS')
app.config['MYSQL_DB'] = os.getenv('DB_NAME')

mysql = MySQL(app)

# ✅ Load your advanced model
advanced_model = pickle.load(open('advanced_model.pkl', 'rb'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        age = int(request.form['age'])
        gender = request.form['gender']
        height = float(request.form['height'])
        weight = float(request.form['weight'])
        goal = request.form['goal']
        activity_level = float(request.form['activity_level'])
        target_weight = float(request.form['target_weight'])
        target_date = request.form['target_date']

        # ✅ Calculate BMR
        if gender.lower() == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        bmr *= activity_level

        cursor = mysql.connection.cursor()
        cursor.execute(
            '''INSERT INTO users 
               (name, email, password, age, gender, height, weight, goal, 
                activity_level, target_weight, target_date, bmr) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (name, email, password, age, gender, height, weight, goal,
             activity_level, target_weight, target_date, bmr)
        )
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        identifier = request.form['identifier']  # username OR email
        password_input = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s OR name = %s', (identifier, identifier))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password_input):
            session['loggedin'] = True
            session['id'] = user['id']
            session['name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            msg = 'Incorrect username/email or password!'
    return render_template('login.html', msg=msg)

@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        name = session['name']
        user_id = session['id']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Get goal
        cursor.execute('SELECT goal FROM users WHERE id = %s', [user_id])
        user = cursor.fetchone()
        goal = user['goal']

        # Get workouts
        cursor.execute('SELECT name FROM workouts WHERE goal = %s', [goal])
        workouts = [row['name'] for row in cursor.fetchall()]

        # Get meals
        cursor.execute('SELECT name FROM meals WHERE goal = %s', [goal])
        meals = [row['name'] for row in cursor.fetchall()]

        # Get latest recommendation
        cursor.execute('SELECT recommendation FROM recommendations WHERE user_id = %s ORDER BY date DESC LIMIT 1', [user_id])
        rec = cursor.fetchone()
        recommendation = rec['recommendation'] if rec else 'No recommendation yet.'

        # Get progress history (date, weight, calories)
        cursor.execute('SELECT date, weight, calories FROM progress WHERE user_id = %s ORDER BY date', [user_id])
        rows = cursor.fetchall()
        dates = [str(row['date']) for row in rows]
        weights = [row['weight'] for row in rows]
        calories = [row['calories'] for row in rows]

        cursor.close()

        return render_template(
            'dashboard.html',
            name=name,
            workouts=workouts,
            meals=meals,
            recommendation=recommendation,
            dates=dates,
            weights=weights,
            calories=calories
        )

    return redirect(url_for('login'))

@app.route('/progress', methods=['POST'])
def progress():
    if 'loggedin' in session:
        user_id = session['id']
        weight = float(request.form['weight'])
        calories = int(request.form['calories'])
        protein = float(request.form['protein'])
        carbs = float(request.form['carbs'])
        fat = float(request.form['fat'])
        workout_type = request.form['workout_type']
        duration = int(request.form['duration'])
        intensity = request.form['intensity']
        steps = int(request.form['steps'])
        notes = request.form['notes']

        today = date.today()

        # Pull user info
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT age, gender, height FROM users WHERE id = %s', [user_id])
        user = cursor.fetchone()

        gender_num = 1 if user['gender'].lower() == 'male' else 0

        X_input = [[
            user['age'],
            gender_num,
            user['height'],
            weight,
            calories,
            protein,
            carbs,
            fat,
            duration,
            steps
        ]]

        # Load model & predict
        prediction = advanced_model.predict(X_input)[0]
        prediction = round(prediction, 2)

        result = f'✅ Estimated next week weight: {prediction} kg'

        # Save progress
        cursor.execute(
            '''INSERT INTO progress 
               (user_id, date, weight, calories, protein, carbs, fat, workout_type, duration, intensity, steps, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
            (user_id, today, weight, calories, protein, carbs, fat, workout_type, duration, intensity, steps, notes)
        )

        # Save recommendation
        cursor.execute(
            'INSERT INTO recommendations (user_id, date, recommendation) VALUES (%s, %s, %s)',
            (user_id, today, result)
        )

        mysql.connection.commit()
        cursor.close()

        return render_template('progress_result.html', result=result)
    return redirect(url_for('login'))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    user_id = session['id']
    msg = ''

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        name = request.form['name']
        age = int(request.form['age'])
        gender = request.form['gender']
        height = float(request.form['height'])
        weight = float(request.form['weight'])
        goal = request.form['goal']
        activity_level = float(request.form['activity_level'])
        target_weight = float(request.form['target_weight'])
        target_date = request.form['target_date']

        # ✅ Recalculate BMR (Mifflin-St Jeor)
        if gender.lower() == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        bmr *= activity_level

        cursor.execute('''
            UPDATE users
            SET name = %s, age = %s, gender = %s, height = %s, weight = %s,
                goal = %s, activity_level = %s, target_weight = %s, target_date = %s, bmr = %s
            WHERE id = %s
        ''', (name, age, gender, height, weight, goal, activity_level, target_weight, target_date, bmr, user_id))

        mysql.connection.commit()
        msg = '✅ Profile updated successfully!'

    # Load current user data
    cursor.execute('SELECT * FROM users WHERE id = %s', [user_id])
    user = cursor.fetchone()

    cursor.close()

    return render_template('profile.html', user=user, msg=msg)


@app.route('/send_reminders')
def send_reminders():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT email, name FROM users WHERE email != %s', [app.config['MAIL_DEFAULT_SENDER']])
    users = cursor.fetchall()
    cursor.close()

    for user in users:
        msg = Message(
            'Daily Progress Reminder',
            recipients=[user['email']],
            body=f"Hi {user['name']},\n\nDon't forget to log your fitness progress today!\n\nStay healthy! 🚀"
        )
        mail.send(msg)

    return '✅ Reminders sent!'

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    msg = ''
    if request.method == 'POST':
        current = request.form['current']
        new = request.form['new']
        confirm = request.form['confirm']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT password FROM users WHERE id = %s', [session['id']])
        user = cursor.fetchone()

        if not check_password_hash(user['password'], current):
            msg = '❌ Current password incorrect!'
        elif new != confirm:
            msg = '❌ New passwords do not match!'
        else:
            hashed = generate_password_hash(new)
            cursor.execute('UPDATE users SET password = %s WHERE id = %s', (hashed, session['id']))
            mysql.connection.commit()
            msg = '✅ Password changed successfully!'

        cursor.close()

    return render_template('change_password.html', msg=msg)

@app.route('/admin')
def admin_dashboard():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT is_admin FROM users WHERE id = %s', [session['id']])
    user = cursor.fetchone()

    if not user or not user['is_admin']:
        return '❌ Access denied.'

    cursor.execute('SELECT id, name, email, goal, age, gender FROM users')
    all_users = cursor.fetchall()
    cursor.close()

    return render_template('admin_dashboard.html', users=all_users)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('name', None)
    return redirect(url_for('index'))

@app.route('/forecast')
def forecast():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    user_id = session['id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(
        'SELECT date, weight FROM progress WHERE user_id = %s ORDER BY date',
        [user_id]
    )
    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        return "❌ Not enough data to forecast!"

    # Prepare DataFrame
    import pandas as pd
    df = pd.DataFrame(rows)
    df.rename(columns={'date': 'ds', 'weight': 'y'}, inplace=True)

    # Fit Prophet
    model = Prophet()
    model.fit(df)

    # Future dataframe
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)

    # Create Plotly chart
    actual_trace = go.Scatter(
        x=df['ds'], y=df['y'], mode='markers+lines', name='Actual Weight'
    )
    forecast_trace = go.Scatter(
        x=forecast['ds'], y=forecast['yhat'], mode='lines', name='Forecast'
    )

    layout = go.Layout(
        title='Weight Forecast (Next 30 Days)',
        xaxis={'title': 'Date'},
        yaxis={'title': 'Weight (kg)'}
    )

    fig = go.Figure(data=[actual_trace, forecast_trace], layout=layout)
    plot_div = pyo.plot(fig, output_type='div')

    return render_template('forecast.html', plot_div=plot_div)

if __name__ == '__main__':
    app.run(debug=True)
