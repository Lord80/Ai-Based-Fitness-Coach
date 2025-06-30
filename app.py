from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import date
import pickle
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'lord'
app.config['MYSQL_PASSWORD'] = '2005'
app.config['MYSQL_DB'] = 'fitness_ai'


# Load your trained model
model = pickle.load(open('progress_model.pkl', 'rb'))

mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        age = request.form['age']
        gender = request.form['gender']
        height = request.form['height']
        weight = request.form['weight']
        goal = request.form['goal']

        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO users (name, email, password, age, gender, height, weight, goal) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                       (name, email, password, age, gender, height, weight, goal))
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
        cursor.execute('SELECT goal FROM users WHERE id = %s', [user_id])
        user = cursor.fetchone()
        goal = user['goal']

        cursor.execute('SELECT name FROM workouts WHERE goal = %s', [goal])
        workouts = [row['name'] for row in cursor.fetchall()]

        cursor.execute('SELECT name FROM meals WHERE goal = %s', [goal])
        meals = [row['name'] for row in cursor.fetchall()]

        # Get latest recommendation if any
        cursor.execute('SELECT recommendation FROM recommendations WHERE user_id = %s ORDER BY date DESC LIMIT 1', [user_id])
        rec = cursor.fetchone()
        recommendation = rec['recommendation'] if rec else 'No recommendation yet.'

        cursor.close()

        return render_template('dashboard.html', name=name, workouts=workouts, meals=meals, recommendation=recommendation)

    return redirect(url_for('login'))


@app.route('/progress', methods=['POST'])
def progress():
    if 'loggedin' in session:
        user_id = session['id']
        weight = float(request.form['weight'])
        calories = int(request.form['calories'])
        notes = request.form['notes']

        today = date.today()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT goal FROM users WHERE id = %s', [user_id])
        user = cursor.fetchone()
        goal = user['goal'].strip().lower()
        goal_num = 0 if 'loss' in goal else 1

        prediction = model.predict([[weight, calories, goal_num]])[0]

        if prediction == 1:
            result = "✅ You’re on track! Keep it up!"
        else:
            result = "⚠️ You might need to adjust: Try more exercise or tweak calories."

            # Optional: Auto-change goal in DB? Not recommended yet, better to recommend.
            # Example:
            # new_goal = 'Weight Loss' if goal_num == 1 else 'Weight Gain'
            # cursor.execute('UPDATE users SET goal = %s WHERE id = %s', (new_goal, user_id))

        # Save progress
        cursor.execute(
            'INSERT INTO progress (user_id, date, weight, calories, notes) VALUES (%s, %s, %s, %s, %s)',
            (user_id, today, weight, calories, notes)
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


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('name', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
