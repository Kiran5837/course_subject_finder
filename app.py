from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from search import setup, main, fetch_course_prefix_from_database, fetch_course_titles_from_database
import time

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@app.route('/api/course_titles', methods=['GET'])
def get_course_titles():
    course_prefix = request.args.get('course_prefix')

    # fetch course titles from your database
    course_titles = fetch_course_titles_from_database(course_prefix)

    return jsonify({
        'course_titles': course_titles
    })

@app.route('/api/course_prefixes', methods=['GET'])
def get_course_prefixes():
    prefix_query = request.args.get('query')

    # fetch course prefixes from your database
    course_prefixes = fetch_course_prefix_from_database(prefix_query)

    return jsonify({
        'course_prefixes': course_prefixes
    })

@app.route('/api/course_subject', methods=['POST'])
def course_subject():
    try:
        data = request.get_json()
        course_prefix = data['course_prefix']
        course_title = data['course_title']

        print(f"Course Prefix: {course_prefix}")
        print(f"Course Title: {course_title}")
        
        if len(course_prefix) > 10 or len(course_title) > 100:
            return jsonify({"error": "Input length exceeds the limit."}), 400

        start_time = time.time()
        output_subject, similarity_rate, fetched_dept_names = main(course_prefix, course_title)
        execution_time = time.time() - start_time

        print(f"Execution time: {execution_time}")

        # Convert fetched_dept_names to a list before including it in the response.
        fetched_dept_names = list(fetched_dept_names)

        return jsonify({'course_subject': output_subject, 'similarity_rate': similarity_rate, 'department_abbreviations': fetched_dept_names})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    setup()  # Call setup before starting the Flask application
    app.run(debug=True)
