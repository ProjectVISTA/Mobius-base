from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import os
import datetime

app = Flask(__name__)
app.secret_key = "fortinet"  # Change this to a secure key

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

Speed_test_1_download_name = 'PC Download Speed (Mbps)'
Speed_test_1_upload_name = 'PC Upload Speed (Mbps)'
Speed_test_2_download_name = 'FortiGate Download Speed (Mbps)'
Speed_test_2_upload_name = 'FortiGate Upload Speed (Mbps)'
Speed_test_3_download_name = 'SSL-VPN Download Speed (Mbps)'
Speed_test_3_upload_name = 'SSL-VPN Upload Speed (Mbps)'
Threshold_value = 30

checkbox_html = '<input type="checkbox" name="checkboxes" class="required-checkbox" style="width: 20px; height: 20px; accent-color: red; border: 2px solid black; border-radius: 4px; margin: 5px;">'
#in the current implementation: one textarea per step
text_area_html = '<br><textarea maxlength="1500" name="textinput1" class="textinput1" id="textinput1" placeholder="Please enter the output for the above commands here (Optional - max 1500 Chars)"></textarea>'

troubleshooting_steps = [
    {
        "step": "Enable DTLS",
        "question": f''' 
<h2><b>Enable DTLS if not done so by following the link below.</b></h2>
-> Please verify that the DTLS is being used either by pcap to identify DTLS encapsulation or from CLI.
->  Check if the above changes improve the speeds
''',
        "options": ["Performance increased", "Issue still persists"],
        "next": {"Performance increased": "Troubleshooting done", "Issue still persists": "Packet drop check in SSL-VPN daemon"}
    },
    {
        "step": "Packet drop check in SSL-VPN daemon",
        "question": f''' 
<h2><b>Check for Drops in SSL-VPN</b></h2>
{checkbox_html} 1. Run the following diagnostics on FortiGate: 
    diagnose vpn ssl statistics
    diagnose vpn ssl mux-stat
    diagnose sys udpsock
    diagnose sys tcpsock
    fnsysctl ifconfig ssl.root (in case of vdoms replace root with vdom)

Please provide the output for commands in the previous step:
{text_area_html}
{checkbox_html} 2. If drops are still seen, look into the cause of it.
{checkbox_html} 3. If no drops are seen, please proceed.
''',
        "info": "Packet drops in SSL-VPN may indicate network congestion, firewall issues, or misconfigurations. Checking diagnostic commands can help pinpoint the cause.",
        "options": ["No drops seen", "drops seen still"],
        "next": {"No drops seen": "pcap analysis", "drops seen still": "Escalate/Swarm"}
    },
]

@app.route("/", methods=["GET", "POST"])
def index():
    session.clear()
    return render_template("index.html")

@app.route("/troubleshoot", methods=["GET", "POST"])
def troubleshoot():
    if request.method == "POST":
        choice = request.form.get("choice")
        action = request.form.get("action")
        current_step = session.get("current_step", 0)

        if action == "back":
            if current_step > 0:
                session["current_step"] -= 1
                session["current_question"] = troubleshooting_steps[session["current_step"]]["question"]
            return redirect(url_for("troubleshoot"))

        checked_boxes = request.form.getlist("checkboxes")
        bypass_reason = request.form.get("bypass_reason", "").strip()
        textinput1 = request.form.get("textinput1", "").strip()

        if len(checked_boxes) < troubleshooting_steps[current_step]["question"].count("name=\"checkboxes\"") and not bypass_reason:
            flash("Please check all required checkboxes or provide a bypass reason.", "error")
            return redirect(url_for("troubleshoot"))

        step_report = f"Step {current_step+1}: {troubleshooting_steps[current_step]['step']} -> Answer: {choice}"
        if bypass_reason:
            step_report += f" (Bypassed with reason: {bypass_reason})"
        if textinput1:
            step_report += f"\n  Command output: \n{textinput1}\n\n"
        session.setdefault("report", []).append(step_report)

        next_step = troubleshooting_steps[current_step]["next"].get(choice, None)
        if next_step in [step["step"] for step in troubleshooting_steps]:
            session["current_step"] = next(i for i, step in enumerate(troubleshooting_steps) if step["step"] == next_step)
            session["current_question"] = troubleshooting_steps[session["current_step"]]["question"]
        else:
            session["current_question"] = "Troubleshooting complete."
            session["current_step"] = -1

    if "current_question" not in session:
        session["current_step"] = 0
        session["current_question"] = troubleshooting_steps[0]["question"]

    step_data = troubleshooting_steps[session["current_step"]] if session["current_step"] != -1 else {}
    options = step_data.get("options", [])
    info = step_data.get("info", "")

    return render_template("troubleshoot.html", question=session["current_question"], options=options, info=info, show_back=session.get("current_step", 0) > 0, messages=list(session.pop("_flashes", [])))

@app.route("/download_report")
def download_report():
    filename = f"troubleshooting_report_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    with open(filepath, "w") as f:
        f.write("\n".join(session.get("report", [])))
    
    return send_file(filepath, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8869)