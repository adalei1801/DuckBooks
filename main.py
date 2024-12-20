from flask import Flask, render_template, request, redirect, flash, abort
import flask_login
import pymysql
from dynaconf import Dynaconf

app = Flask(__name__)

conf = Dynaconf(
    settings_file = ["settings.toml"]
)

app.secret_key = conf.secret_key

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = ("/signin")

class User:
    is_authenticated = True
    is_anonymous = False
    is_active = True

    def __init__(self, user_id, username, email, name):
        self.id = user_id
        self.username = username
        self.email = email
        self.name = name

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM `Customer` WHERE `id` = {user_id}; ")

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result is not None:
        return User(result["id"], result["username"], result["email"], result["name"])
    


def connect_db():
    conn = pymysql.connect(
        host = "10.100.34.80",
        database = "aking_duck_books",
        user = "aking",
        password = conf.password,
        autocommit = True,
        cursorclass = pymysql.cursors.DictCursor
    )

    return conn

@app.route("/")
def index():
    return render_template("homepage.html.jinja")



@app.route("/browse")
def product_browse():
    query = request.args.get('query')

    conn = connect_db()

    cursor = conn.cursor()

    if query is None:
        cursor.execute("SELECT * FROM `Product` ;")
    else:
        cursor.execute(f"SELECT * FROM `Product` WHERE `title` LIKE '%{query}%' OR `author` LIKE '%{query}%';")

    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("browse.html.jinja", products = results)


@app.route("/product/<product_id>")
def product_page(product_id):
    conn = connect_db()

    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM `Product` WHERE `id` = {product_id} ;")

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result is None:
        abort(404)

    return render_template("product.html.jinja", product = result)


@app.route("/product/<product_id>/cart", methods=["POST"])
@flask_login.login_required
def add_to_cart(product_id):
    customer_id = flask_login.current_user.id
    quantity = request.form["quantity"]
    
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(f"""
    INSERT INTO `Cart`
    (`product_id`, `customer_id`, `quantity`)
    VALUES
    ({product_id}, {customer_id}, {quantity});
    """)
    
    cursor.close()
    conn.close

    return redirect("/cart")


@app.route("/signin", methods=["POST", "GET"])
def signin():
    if flask_login.current_user.is_authenticated: 
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(f"SELECT * FROM `Customer` WHERE `username` = '{username}' ;")

        result = cursor.fetchone()

        if result is None:
            flash("This username/password is incorrect")
        elif password != result["password"]: 
            flash("This username/password is incorrect")
        else:
            user = User(result["id"], result["username"], result["email"], result["name"])
            flask_login.login_user(user)
            return redirect("/")
        
        cursor.close()
        conn.close

    return render_template("signin.html.jinja")

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect("/signin")

@app.route("/signup", methods=["POST", "GET"])
def signup():
    if flask_login.current_user.is_authenticated: 
        return redirect("/")
    
    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]
        con_pass = request.form["con_pass"]
        email = request.form["email"]
        address = request.form["address"]
        card_num = request.form["card_num"]
        phone = request.form["phone"]
        birthday = request.form["bday"]
        country = request.form["country"]

        if password != con_pass:
            flash("Password does not match")
            return render_template("signup.html.jinja")
        
        if len(password) < 8:
            flash("Password is too short")
            return render_template("signup.html.jinja")
        

        conn = connect_db()
        cursor = conn.cursor()

        try:
            cursor.execute(f""" 
            INSERT INTO `Customer`
                (`name`, `username`, `password`, `card_number`, `address`, `email`, `birthday`, `country`, `phone_number`)
            VALUES
                ('{name}', '{username}', '{password}', '{card_num}', '{address}', '{email}', '{birthday}', '{country}', '{phone}' );
            """)
        except pymysql.err.IntegrityError:
            flash("Sorry, that value is already in use")
        else: 
            return redirect("/signin")
        finally:
            cursor.close()
            conn.close
    

    return render_template("signup.html.jinja")

@app.route("/cart")
@flask_login.login_required
def cart():
    return render_template("cart.html.jinja")