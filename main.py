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
    conn = connect_db()

    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM `Product` WHERE `genre` LIKE 'dystopia%';")

    result_dystopia = cursor.fetchall()

    cursor.execute(f"SELECT * FROM `Product` WHERE `genre` LIKE '%fiction';")

    result_fiction = cursor.fetchall()

    cursor.execute(f"SELECT * FROM `Product` WHERE `page` <= '300';")

    result_short = cursor.fetchall()


    cursor.close()
    conn.close()
    return render_template("homepage.html.jinja", products_dystopia=result_dystopia, products_fiction=result_fiction, products_short=result_short)



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

    cursor.execute(f"""
        SELECT
            *
        FROM `Review`     
        JOIN `Customer` ON `customer_id` = `Customer`.`id`
                   """)
    
    review_results = cursor.fetchall()


    cursor.close()
    conn.close()

    if result is None:
        abort(404)

    return render_template("product.html.jinja", product = result, product_review = review_results)


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
    ({product_id}, {customer_id}, {quantity})
    ON DUPLICATE KEY UPDATE  `quantity` = `quantity` + {quantity};
    """)
    
    cursor.close()
    conn.close()

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
        conn.close()

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
            conn.close()
    

    return render_template("signup.html.jinja")

@app.route("/cart")
@flask_login.login_required
def cart():
    conn = connect_db()
    cursor = conn.cursor()

    customer_id = flask_login.current_user.id

    cursor.execute(f""" 
                    SELECT 
                        `title`,
                        `author`,
                        `price`,
                        `quantity`,
                        `image`,
                        `product_id`,
                        `Cart`.`id`
                    FROM `Cart`
                    JOIN `Product` ON `product_id` = `Product`.`id`
                    WHERE `customer_id` = {customer_id};
                        """)

    results = cursor.fetchall()
    price = 0

    for product in results:
        item_total = product['price'] * product['quantity']
        price += item_total

    cursor.close()
    conn.close()

    return render_template("cart.html.jinja", products=results, price=price)

@app.route("/cart/<cart_id>/delete", methods=["POST"])
@flask_login.login_required
def delete(cart_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(f"DELETE FROM `Cart` WHERE `id`= {cart_id};")

    cursor.close()
    conn.close()

    return redirect("/cart")

@app.route("/update/<cart_id>/update", methods=["POST"])
@flask_login.login_required
def update(cart_id):
    conn = connect_db()
    cursor = conn.cursor()

    quantity = request.form["quantity"]

    cursor.execute(f"""
                    UPDATE `Cart`
                    SET `quantity`= {quantity}
                    WHERE `id` = {cart_id};
    """)

    cursor.close()
    conn.close()

    return redirect("/cart")

@app.route("/checkout")
@flask_login.login_required
def checkout():
    conn = connect_db()
    cursor = conn.cursor() 

    customer_id = flask_login.current_user.id

    cursor.execute(f""" 
                    SELECT 
                        `title`,
                        `author`,
                        `price`,
                        `quantity`,
                        `image`,
                        `product_id`,
                        `Cart`.`id`
                    FROM `Cart`
                    JOIN `Product` ON `product_id` = `Product`.`id`
                    WHERE `customer_id` = {customer_id};
                        """)
    
    results = cursor.fetchall()

    cursor.execute(f""" 
                    SELECT 
                        `name`,
                        `card_number`,
                        `address`,
                        `phone_number`,
                        `email`,
                        `name`,
                        `country`,
                        `customer_id`,
                        `Cart`.`id`
                    FROM `Cart`
                    JOIN `Customer` ON `customer_id` = `Customer`.`id`
                    WHERE `customer_id` = {customer_id};
                        """)

    results_customer = cursor.fetchone()
    price = 0

    for product in results:
        item_total = product['price'] * product['quantity']
        price += item_total
    
    cursor.close()
    conn.close()

    return render_template("checkout.html.jinja", products=results, price=price, customer=results_customer)

@app.route("/cart/buy", methods=["POST"])
@flask_login.login_required
def buy():
    conn = connect_db()
    cursor = conn.cursor() 

    customer_id = flask_login.current_user.id

    address = request.form["address"]
    country = request.form["country"]

    cursor.execute(f"""
        INSERT INTO `Sale`
            (`customer_id`, `address`, `country`)
        VALUES
            ({customer_id}, '{address}', '{country}');
            """)
    
    sale_id = cursor.lastrowid
    cursor.execute(f"SELECT * FROM `Cart` WHERE `customer_id` = {customer_id}; ")

    results = cursor.fetchall()

    for item in results:
        cursor.execute(f""" 
        INSERT INTO `SaleProduct`
            (`sale_id`, `product_id`, `quantity`)
        VALUES
            ({sale_id}, {item['product_id']}, {item['quantity']});
        """)



    cursor.execute(f"DELETE FROM `Cart` WHERE `customer_id` = {customer_id};")

    cursor.close()
    conn.close()

    return redirect("/thankyou")

@app.route("/thankyou")
@flask_login.login_required
def thankyou():
    return render_template("thankyou.html.jinja")


@app.route("/product/<product_id>/review", methods=["POST"])
@flask_login.login_required
def review(product_id):
    conn = connect_db()
    cursor = conn.cursor() 

    customer_id = flask_login.current_user.id

    rating = request.form['rating']
    comment = request.form['comment']


    cursor.execute(f"""
    INSERT INTO `Review`
    (`product_id`, `customer_id`, `rating`, `comment`)
    VALUES
    ({product_id}, {customer_id}, {rating}, '{comment}');
    """)

    cursor.close()
    conn.close()

    return redirect(f"/product/{product_id}")
