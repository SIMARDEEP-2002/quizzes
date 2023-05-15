from flask import Flask, jsonify, request
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://username:password@localhost/database_name'
db = SQLAlchemy(app)

scheduler = BackgroundScheduler()
scheduler.start()

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    options = db.Column(db.JSON, nullable=False)
    right_answer = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False)


db.create_all()


@app.route('/quizzes', methods=['POST'])
def create_quiz():
    data = request.get_json()

    question = data.get('question')
    options = data.get('options')
    right_answer = data.get('rightAnswer')
    start_date = data.get('startDate')
    end_date = data.get('endDate')

    if not (question and options and right_answer and start_date and end_date):
        return jsonify({'error': 'Invalid request data'}), 400

    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    quiz = Quiz(
        question=question,
        options=options,
        right_answer=right_answer,
        start_date=start_date,
        end_date=end_date,
        status='inactive'
    )

    db.session.add(quiz)
    db.session.commit()

    # Schedule quiz status update based on start and end date
    scheduler.add_job(update_quiz_status, 'date', run_date=start_date, args=[quiz.id, 'active'])
    scheduler.add_job(update_quiz_status, 'date', run_date=end_date, args=[quiz.id, 'finished'])

    return jsonify({'message': 'Quiz created successfully'}), 201


def update_quiz_status(quiz_id, status):
    quiz = Quiz.query.get(quiz_id)
    if quiz:
        quiz.status = status
        db.session.commit()


@app.route('/quizzes/active', methods=['GET'])
def get_active_quiz():
    now = datetime.now()

    active_quiz = Quiz.query.filter(Quiz.start_date <= now, Quiz.end_date >= now).first()

    if active_quiz:
        return jsonify(active_quiz)
    else:
        return jsonify({'message': 'No active quiz found'}), 404


@app.route('/quizzes/<int:quiz_id>/result', methods=['GET'])
def get_quiz_result(quiz_id):
    quiz = Quiz.query.get(quiz_id)

    if quiz:
        if datetime.now() > quiz.end_date:
            return jsonify({'result': quiz.right_answer})
        else:
            return jsonify({'message': 'Quiz is not finished yet'}), 400
    else:
        return jsonify({'message': 'Quiz not found'}), 404


@app.route('/quizzes/all', methods=['GET'])
def get_all_quizzes():
    all_quizzes = Quiz.query.all()
    return jsonify({'quizzes': [quiz.__dict__ for quiz in all_quizzes]})


if __name__ == '__main__':
    app.run(debug=True)
