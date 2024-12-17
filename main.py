from flask import Flask, render_template, request, redirect, flash
import pymysql
from dynaconf import Dynaconf

app = Flask(__name__)

conf = Dynaconf(
    settings_file = ["settings.toml"]
)

app.secret_key = conf.secret_key

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
    conn = connect_db()

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM `Product` ;")

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

    return render_template("product.html.jinja", product = result)

@app.route("/signin")
def signin():
    return render_template("signin.html.jinja")

@app.route("/signup", methods=["POST", "GET"])
def signup():
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