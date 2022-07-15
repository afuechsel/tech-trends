import sqlite3
import sys
import logging

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort
from urllib.request import pathname2url

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    try: 
        dburi = 'file:{}?mode=rw'.format(pathname2url('database.db'))
        connection = sqlite3.connect(dburi, uri=True)
        connection.row_factory = sqlite3.Row
        app.config['totalConnectionCount'] += 1
        app.config['healthy'] = True
        return connection
    except: 
        app.logger.error('Database is not available')
        app.config['healthy'] = False
        raise

# Function to get a post using its ID
def get_post(post_id):
    try:
        connection = get_db_connection()
        post = connection.execute('SELECT * FROM posts WHERE id = ?',
                            (post_id,)).fetchone()
        connection.close()
        return post
    except: 
        app.config['healthy'] = False
        return None

# Define the Flask application
app = Flask(__name__)
# counts the total number of connections for the /metrics endpoint
app.config['totalConnectionCount'] = 0
# stores the health status 
app.config['healthy'] = True

# Define the main route of the web application 
@app.route('/')
def index():
    try: 
        connection = get_db_connection()
        posts = connection.execute('SELECT * FROM posts').fetchall()
        connection.close()
        return render_template('index.html', posts=posts)
    except: 
        app.config['healthy'] = False

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    if post is None:
      app.logger.warning('Post %d was not found' % post_id)
      return render_template('404.html'), 404
    else:
      app.logger.debug('Retrieved article (id=%d) with title "%s"' % (post_id, post['title']))
      return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.debug('"About Us" was called')
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            try: 
                connection = get_db_connection()
                connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                            (title, content))
                connection.commit()
                connection.close()
                app.logger.info('Created new article with title "%s"' % title)
            except: 
                app.config['healthy'] = False
            return redirect(url_for('index'))

    return render_template('create.html')

# Define the healthcheck endpoint
@app.route('/healthz')
def status():
    if app.config['healthy']: 
        response = app.response_class(
            response=json.dumps({"result": "OK - healthy"}),
            status=200,
            mimetype='application/json'
        )
    else:
        response = app.response_class(
            response=json.dumps({"result": "ERROR - unhealthy"}),
            status=500,
            mimetype='application/json'
        )
    return response

# Define the metrics endpoint
@app.route('/metrics')
def metrics():
    postCount = getPostCount()
    response = app.response_class(
        response=json.dumps({"status": "success", "data": {
                            "db_connection_count": app.config['totalConnectionCount'], "post_count": postCount}}),
        status=200,
        mimetype='application/json'
    )
    return response

# Get the count of posts in the database
def getPostCount():
    try: 
        connection = get_db_connection()
        count = connection.execute('SELECT COUNT(*) FROM posts').fetchone()
        connection.close()
        return count[0]
    except: 
        app.config['healthy'] = False
        return 0

# start the application on port 3111
if __name__ == "__main__":
    # logging DEBUG and INFO goes to stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)

    # logging WARNING and above goes to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.addFilter(lambda record: record.levelno > logging.INFO)
    handlers = [stderr_handler, stdout_handler]
    format_output = '%(levelname)s: [%(asctime)s] %(message)s'
    logging.basicConfig(format=format_output, level=logging.DEBUG, handlers=handlers)

    # start the app
    app.run(host='0.0.0.0', port='3111')
