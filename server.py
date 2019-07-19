from flask import Flask, render_template, request, redirect, session, flash
import re, time
from mysqlconnection import connectToMySQL
from flask_bcrypt import Bcrypt
import sys

app = Flask(__name__)
app.secret_key='alo'
bcrypt = Bcrypt(app)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

@app.route("/")
def index():
    return render_template("index.html")


@app.route('/registration', methods=['POST'])
def add_info():
    is_valid = True
    if len(request.form['username']) < 1:
        flash("User name at least 5 character", 'username')
        is_valid = False
    if not EMAIL_REGEX.match(request.form['email']):  # test whether a field matches the pattern
        flash("Re-enter email for format email@email.email", 'email')
        is_valid = False
    email=request.form['email']
    query = "SELECT * FROM users WHERE email = %(email)s;"
    data = {"email": request.form["email"]}
    mysql = connectToMySQL('dojo_book')
    users_email=mysql.query_db(query, data)
    count=0
    for user_email in users_email:
        if user_email['email']==email:
            count+=1
    print(count)
    if count==0:
        pass
    if count!=0:
        flash("email exist", 'email')
        is_valid = False
    if  len(request.form['password1']) < 8:
        flash("password need 8 character", 'password1')
        is_valid = False
    if (request.form['password1'])!= (request.form['password2']):
        flash("Password not match", 'password2')
        is_valid = False
    if not is_valid:
        return redirect("/")
    else:

        pw_hash = bcrypt.generate_password_hash(request.form['password1'])
        data = {
            'username': request.form['username'],
            'alias': request.form['alias'],
            'email': request.form['email'],
            'pw_hash': pw_hash
        }
        query='INSERT INTO users(name, alias, email, pw_hash) VALUES (%(username)s, %(alias)s, %(email)s, %(pw_hash)s )'
        mysql=connectToMySQL('dojo_book')
        user_id = mysql.query_db(query, data)
        session['user_id'] = int(user_id)
        return redirect(f'/success')

@app.route('/login', methods=['POST'])
def logged_in():
    mysql = connectToMySQL('dojo_book')
    query = "SELECT * FROM users WHERE email = %(email)s;"
    data = {"email": request.form["login_email"]}
    result = mysql.query_db(query, data)
    if len(result) > 0:
        if bcrypt.check_password_hash(result[0]['pw_hash'], request.form['login_password']):
            session['user_id'] = result[0]['id']

            return redirect(f'/success')
    else :
        flash("Email is not valid or Password is wrong dude", 'password_log')
        return redirect("/")


@app.route('/success')
def success_log_in():
    user_id=session['user_id']
    data = {
        'user_id':user_id
    }
    query = 'SELECT name, id from users where id =%(user_id)s'
    mysql = connectToMySQL('dojo_book')
    user = mysql.query_db(query, data)
    user_name=user[0]['name']
    user_id = user_id
    mysql = connectToMySQL('dojo_book')
    query = 'SELECT * from (select users.name, reviews.rating, reviews.comment, reviews.created_at, ' \
            'books.title, books.id as book_id from reviews join books on reviews.book_id = books.id ' \
            'join users on reviews.book_id = users.id)as t order by created_at desc limit 3'
    reviews = mysql.query_db(query)
    for review in reviews:
        review['rating']=int(review['rating'])
        review['created_at']= review['created_at'].strftime(' %b %d, %Y')
    mysql = connectToMySQL('dojo_book')
    query = 'Select title, id from books'
    books = mysql.query_db(query)
    return render_template('books.html', user_name=user_name, reviews=reviews, books=books, user_id = user_id)


@app.route('/books/add')
def templates():
    mysql = connectToMySQL('dojo_book')
    query = 'Select author from books'
    authors = mysql.query_db(query)
    return render_template('rating.html', authors=authors)

@app.route('/books/add_review', methods=['POST'])
def add_review():
    user_id = session['user_id']
    print(request.form['book_title'])
    if len(request.form['book_title'])<1:
        return redirect(f'/books/add')
    mysql = connectToMySQL('dojo_book')
    query = 'Select title from books'
    books_name = mysql.query_db(query)
    for book_name in books_name:
        if book_name['title'] == request.form['book_title']:
            print("book is exist in database")
            flash("book is exist in database", 'book_exist')
            return redirect(f'/books/add')
    if len(request.form['author2']) > 0:
        author = request.form['author2']
    else:
        author = request.form['author1']
    mysql = connectToMySQL('dojo_book')
    data1 ={
        'title': request.form['book_title'],
        'author':author,
    }
    query = 'Insert into books (title, author, created_at, updated_at) VALUES(%(title)s, %(author)s, NOW(), NOW()); '
    book_id = mysql.query_db(query, data1)
    mysql = connectToMySQL('dojo_book')
    data2={
        'book_id':book_id,
        'user_id': session['user_id'],
        'rating': request.form['star'],
        'review' : request.form['review']
    }
    query = 'Insert into reviews (book_id, user_id, rating, comment, created_at, updated_at) VALUES(%(book_id)s, %(user_id)s, %(rating)s, %(review)s, NOW(), NOW()); '
    mysql.query_db(query, data2)
    return redirect(f'/books/{book_id}')


@app.route('/books/<book_id>')
def book_review(book_id):
    data={
        'book_id':book_id
    }
    query = 'select * from( select reviews.book_id, reviews.rating, reviews.comment, books.title, books.author, ' \
            'reviews.created_at, users.name, users.id as user_id, reviews.id as review_id from reviews left join books on reviews.book_id = books.id ' \
            'join users on users.id = reviews.user_id)' \
            ' as t where book_id = %(book_id)s order by created_at desc limit 3'
    mysql = connectToMySQL('dojo_book')
    reviews = mysql.query_db(query, data)
    print(reviews)
    session['user_id']=int(session['user_id'])
    for review in reviews:
        review['created_at']= review['created_at'].strftime(' %b %d, %Y')
        review['user_id'] = int(review['user_id'])
        return render_template('book_review.html', reviews=reviews)

    if len(reviews)<1 :
        mysql = connectToMySQL('dojo_book')
        query = 'select * from books where id =%(book_id)s'
        book = mysql.query_db(query, data)

        print(book)
        return render_template('book_review.html', book=book)

@app.route('/books/<book_id>/add_new_review', methods=['POST'])
def add_review_to_book(book_id):
    data ={
        'book_id': book_id,
        'user_id': session['user_id'],
        'rating': request.form['star'],
        'review':request.form['review']
    }
    query = 'Insert into reviews (book_id, user_id, rating, comment, created_at, updated_at) ' \
            'VALUES( %(book_id)s, %(user_id)s, %(rating)s,%(review)s, NOW(), NOW())'
    mysql = connectToMySQL('dojo_book')
    mysql.query_db(query, data)
    return redirect(f'/books/{book_id}')


@app.route('/delete/<review_id>/<book_id>')
def delete(review_id, book_id):
    data={
        'review_id':review_id
    }
    query = 'delete from reviews where id = %(review_id)s'
    mysql = connectToMySQL('dojo_book')
    mysql.query_db(query, data)
    return redirect(f'/books/{book_id}')

@app.route('/user/<user_id>')
def show_user(user_id):
    print(user_id)
    data={
        'user_id':user_id
    }
    query = 'select count(title) as count from (select users.name, users.id as user_id, users.email, ' \
            'users.alias, reviews.id, books.title from reviews join users on ' \
            'users.id=reviews.user_id join books on books.id=reviews.book_id ' \
            'where user_id = %(user_id)s) as t'
    mysql = connectToMySQL('dojo_book')
    count=mysql.query_db(query, data)

    query = 'select book_id, title, name, email, user_id from  (select users.name, users.id as user_id, users.email, users.alias, reviews.id, books.title, books.id as book_id from reviews join users on users.id=reviews.user_id join books on books.id=reviews.book_id  ) as t where user_id = 1  group by book_id'
    mysql = connectToMySQL('dojo_book')
    user = mysql.query_db(query, data)
    print(count,'count')
    print(user,'user')
    return render_template('user.html', user=user, count= count)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    print('You have been log out')

    return redirect('/')



if __name__ == "__main__":
    app.run(debug=True)


