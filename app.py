import os
from datetime import datetime
from functools import wraps

from flask import Flask, redirect, session, render_template, request, url_for
from flask_wtf import CSRFProtect

from tools import user_check, user_get, user_manage

app = Flask(__name__)
CSRFProtect(app)
app.secret_key = os.urandom(5000)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("route"))
        if not session["logged_in"] is True:
            return redirect(url_for("route"))
        return f(*args, **kwargs)

    return decorated_function


def no_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("logged_in"):
            if session["logged_in"] is True:
                return redirect(url_for("route"))
        if session.get("username"):
            if session["username"] != "":
                return redirect(url_for("route"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def route():
    if session.get("logged_in"):
        if session["logged_in"]:
            if session.get("username"):
                return redirect(url_for("home"))
    return redirect(url_for("login"))


@app.route("/login")
@no_login
def login():
    error = request.args.get("error")
    if error:
        return render_template("Login.html", error=error)
    return render_template("Login.html")


@app.route("/do_login", methods=["GET", "POST"])
@no_login
def do_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if request.form.get("remember_me"):
            if request.form["remember_me"] == "on":
                session.permanent = True
        if not user_check.check_username(username):
            return redirect("/login?error=login")
        if not user_check.check_verified(username):
            return redirect("/login?error=verified")
        if user_check.check_password(username, password):
            session["logged_in"] = True
            session["username"] = username
        else:
            return redirect("/login?error=login")
    return redirect(url_for("route"))


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("route"))


@app.route("/register")
@no_login
def register():
    error = request.args.get("error")
    if error:
        return render_template("Register.html", error=error)
    return render_template("Register.html")


@app.route("/do_register", methods=["GET", "POST"])
@no_login
def do_register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        password_repeat = request.form["password_repeat"]
        timezone = request.form["timezone"]
        print(timezone)
        if user_check.check_username(username):
            return redirect("/register?error=username")
        elif user_check.check_email(email):
            return redirect("/register?error=email")
        elif not password == password_repeat:
            return redirect("/register?error=password")
        else:
            if user_manage.register(username, email, password, timezone):
                return redirect("/login?error=register_success")
            else:
                return "Error"


@app.route("/home")
@login_required
def home():
    error = request.args.get("error")
    return render_template("Home.html", username=session["username"],
                           running=user_get.get(session["username"], "activeDrive"),
                           startTime=user_get.get_start_time(session["username"]),
                           date_goal=user_get.get(session["username"], "date_goal"),
                           settings_prefill=user_get.get_settings_prefill(session["username"]),
                           error=error, stats=user_get.get_stats(session["username"]))


@app.route("/start_drive", methods=["GET", "POST"])
@login_required
def start_drive():
    if request.method == "POST":
        username = request.form["username"]
        if username == session["username"]:
            if not user_check.check_drive(username):
                return str(user_manage.start_drive(username))


@app.route("/stop_drive", methods=["GET", "POST"])
@login_required
def stop_drive():
    if request.method == "POST":
        username = request.form["username"]
        time_mode = request.form["timemode"]
        if time_mode == "auto":
            if 21 <= int(datetime.now().__format__("%H")) or 5 >= int(datetime.now().__format__("%H")):
                time_mode = "night"

        if username == session["username"]:
            if user_check.check_drive(username):
                return str(user_manage.stop_drive(username, time_mode))


@app.route("/get_stats")
@login_required
def get_stats():
    return render_template("Stats.html", stats=user_get.get_stats(session["username"]))


@app.route("/get_table")
@login_required
def get_table():
    return render_template("Table.html", drives=user_get.get_drive_data(session["username"]))


@app.route("/get_editable_table")
@login_required
def get_editable_table():
    id = request.args.get("id")
    return render_template("EditTable.html", drive=user_get.get_drive(session["username"], id))


@app.route("/edit_data", methods=["GET", "POST"])
@login_required
def edit_data():
    if request.method == "POST":
        start_date = request.form["startDate"]
        start_time = request.form["startTime"]
        stop_time = request.form["stopTime"]
        night = request.form["night"]
        conditions = []
        if night == "true":
            conditions.append("night")
        drive_id = request.form["id"]
        user_manage.update_drive(session["username"], drive_id, start_date, start_time, stop_time, conditions)
        return "Done"


@app.route("/create_drive", methods=["GET", "POST"])
@login_required
def create_drive():
    if request.method == "POST":
        if session["username"] == request.form["username"]:
            user_manage.create_drive(session["username"])


@app.route("/delete_drive", methods=["GET", "POST"])
@login_required
def delete_drive():
    user_manage.remove_drive(session["username"], request.form["id"])
    return "True"


@app.route("/change_settings", methods=["GET", "POST"])
@login_required
def change_settings():
    if request.method == "POST":
        date_goal = request.form["date_goal"]
        goal = request.form["goal"]
        night_goal = request.form["night_goal"]
        if date_goal == "":
            return redirect("/home?error=missing#settings")
        if goal == "" or goal == 0:
            return redirect("/home?error=missing#settings")
        if night_goal == "" or night_goal == 0:
            return redirect("/home?error=missing#settings")
        if user_manage.update_settings(session["username"], date_goal, goal, night_goal):
            return redirect("/home?error=settings_change_success#settings")
        else:
            return redirect("/home?error=settings_change_error#settings")


@app.route("/delete_account_progress")
@login_required
def delete_account_progress():
    return render_template("DeleteAccountProgress.html")


@app.route("/delete_account")
@login_required
def delete_account():
    return render_template("DeleteAccount.html", username=session["username"])


@app.route("/do_delete_account", methods=["GET", "POST"])
@login_required
def do_delete_account():
    if request.method == "POST":
        if request.form["username"] == session["username"]:
            session.clear()
            user_manage.remove_user(request.form["username"])
            return str(user_check.check_username(request.form["username"]))


@app.route("/forgot_password")
def forgot_password():
    return render_template("ForgotPassword.html")


@app.route("/do_request_forgot_password", methods=["GET", "POST"])
def do_request_forgo_password():
    if user_check.check_username(request.form["username"]):
        if user_manage.forgot_password_send_email(request.form["username"]):
            return redirect("/login?error=request_success")
        else:
            return redirect("/login?error=request_error")
    else:
        return redirect("/forgot_password?error=username")


@app.route("/change_password/<string:username>/<string:token>")
def change_password(username, token):
    if user_get.get(username, "password_token") == token:
        return render_template("ChangePassword.html", token=token, username=username)
    else:
        return redirect("/login?error=reset_error")


@app.route("/do_change_password", methods=["GET", "POST"])
def do_change_password():
    if request.method == "POST":
        token = request.form["token"]
        username = request.form["username"]
        password = request.form["password"]
        repeat_password = request.form["password_repeat"]
        if not password == repeat_password:
            return redirect(user_get.get_change_password_error_link(username, token, "password_repeat"))
        elif not user_get.get(username, "password_token") == token:
            return redirect(user_get.get_change_password_error_link(username, token, "unknown"))
        else:
            user_manage.change_password(username, password)
            return redirect("/login?error=change_success")


@app.route("/verify/<string:username>/<string:token>")
@no_login
def verify(username, token):
    if user_manage.verify_user(username, token):
        return redirect("/login?error=verify_complete")
    else:
        return redirect("/login?error=verify_error")


@app.route("/login_check")
def login_check():
    if not session.get("logged_in"):
        return "false"
    elif not session["logged_in"] is True:
        return "false"
    elif not session.get("username"):
        return "false"
    else:
        return "true"


if __name__ == '__main__':
    app.run()
