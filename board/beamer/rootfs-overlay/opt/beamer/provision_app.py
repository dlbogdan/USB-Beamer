import os
import subprocess
import time
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash


APP = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))
APP.secret_key = os.environ.get("FLASK_SECRET", "beamer-secret")

DATA_DIR = "/data"


def write_wpa_supplicant_config(ssid: str, password: str) -> str:
    conf_dir = "/etc/wpa_supplicant"
    os.makedirs(conf_dir, exist_ok=True)
    conf_path = os.path.join(conf_dir, "wpa_supplicant-wlan0.conf")
    content = (
        "ctrl_interface=/var/run/wpa_supplicant\n"
        "update_config=1\n\n"
        "network={\n"
        f"    ssid=\"{ssid}\"\n"
        f"    psk=\"{password}\"\n"
        "}\n"
    )
    with open(conf_path, "w") as f:
        f.write(content)
    os.chmod(conf_path, 0o600)
    return conf_path


def bring_up_station(ssid: str, password: str, timeout_seconds: int = 25) -> bool:
    conf_path = write_wpa_supplicant_config(ssid, password)
    # Delegate network operations to a single shell script call
    result = subprocess.run([
        "/bin/sh", "/usr/scripts/wifi_connect.sh", "wlan0", conf_path, str(timeout_seconds)
    ])
    return result.returncode == 0


def bring_up_ap():
    subprocess.run(["/etc/init.d/S49provision", "start"], check=False)


@APP.route("/wifi", methods=["GET", "POST"])
def wifi():
    if request.method == "POST":
        ssid = request.form.get("ssid", "").strip()
        password = request.form.get("password", "").strip()
        if not ssid or not password:
            flash("SSID and password are required", "error")
            return redirect(url_for("wifi"))
        ok = bring_up_station(ssid, password)
        if ok:
            os.makedirs(DATA_DIR, exist_ok=True)
            Path(os.path.join(DATA_DIR, "provisioned")).write_text("1")
            flash("Connected to Wi‑Fi successfully", "success")
            return redirect(url_for("wifi"))
        else:
            flash("Failed to connect. Check credentials and try again.", "error")
            bring_up_ap()
            return redirect(url_for("wifi"))
    return render_template("wifi.html")


@APP.route("/generate_204")
@APP.route("/hotspot-detect.html")
def captive_probe():
    return ("OK", 200, {"Cache-Control": "no-cache"})

@APP.route("/")
def root_redirect():
    # Any HTTP request to the root gets the Wi‑Fi form
    return redirect(url_for("wifi"))


if __name__ == "__main__":
    port = int(os.environ.get("APP_PORT", 80))
    APP.run(host="0.0.0.0", port=port, debug=True)


