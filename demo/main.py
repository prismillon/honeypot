import tweepy
import winniepot
import secrets
import os

auth = tweepy.OAuthHandler(secrets.API_KEY, secrets.API_KEY_SECRET)
auth.set_access_token(secrets.ACCESS_KEY, secrets.ACCESS_KEY_SECRET)
twitter_client = tweepy.API(auth)
base_bio = "This is an automated honeypot twitter log."

winniepot.STOCKAGE_SERVER = ("prismillon.ddns.net", 5566)


@winniepot.custom_event("on_connection")
def handle_conn():
    if winniepot.LOGFILE != "":
        os.remove(winniepot.LOGFILE)
    winniepot.LOGFILE = ""
    twitter_client.update_status(f"Someone just logged in 🫥")

@winniepot.custom_event("on_ping")
def ping():
    winniepot.log_console(f"{winniepot.session['ip'] if winniepot.session['ip'] != '0' else ''} ping")

@winniepot.custom_event("on_restart")
def compromised_machine():
    if not winniepot.session["connected"] or winniepot.session["ip"] == "0":
        return

    if winniepot.LOGFILE == "":
        return
    try:
        with open(winniepot.LOGFILE, "r") as file:
            message = f"Attacker: {winniepot.session['ip']}\n"
            commands = ""
            for line in file.readlines():
                line = " - ".join(line.split(" - ")[1:])
                if len(message) + len(commands) + len(line) + 3 < 280:
                    commands += f" ▶️ {line}"
            message += commands
    except FileNotFoundError:
        message = f"{winniepot.session['ip']} connected but did not enter any command."

    try:
        twitter_client.update_status(message)
    except tweepy.TweepyException as e:
        print(e)
        print(f"could not post: {message}")
    twitter_client.update_profile(description=base_bio)

@winniepot.custom_event("on_command")
def handle_command(message):
    winniepot.LOGFILE = winniepot.session['ip'] + ".log"
    try:
        twitter_client.update_profile(description=f"{base_bio} We are currently under attack by: {winniepot.session['ip']}. Their last command is: {message}")
    except tweepy.TweepyException as e:
        print(e)
        twitter_client.update_profile(description=f"{base_bio} We are currently under attack by: {winniepot.session['ip']}.")

winniepot.run()