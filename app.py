from flask import Flask, render_template, request, redirect, url_for, session, send_file , flash
import os
import datetime

app = Flask(__name__)
app.secret_key = "fortinet"  # Change this to a secure key

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# for example comparitive analysis
Speed_test_1_download_name = 'PC Download Speed (Mbps)'
Speed_test_1_upload_name = 'PC Upload Speed (Mbps)'
Threshold_value = 30

# Helper function to create input fields
def input_field(name, value=""):
    return f'<input type="text" step="0.01" name="{name}" value="{value}" style="width: 100px; padding: 5px; margin: 5px;">'

# Helper function to create a dropdown
def dropdown(name, text, options):
    html_code = f'<label for="{name}">{text}</label>'
    html_code += f'<select name="{name}" id="{name}">'
    html_code += '<option value="">--Please choose an option--</option>'
    for entry in options:
        html_code += f'<option value="{entry}">{entry}</option>'
    html_code += '</select>'
    return html_code
'''
<label for="fruit">Choose a fruit:</label>
<select name="fruit" id="fruit">
  <option value="">--Please choose an option--</option>
  <option value="apple">Apple</option>
  <option value="banana">Banana</option>
  <option value="orange">Orange</option>
  <option value="mango">Mango</option>
</select>
'''

checkbox_html = '<input type="checkbox" name="checkboxes" class="required-checkbox" style="width: 20px; height: 20px; accent-color: red; border: 2px solid black; border-radius: 4px; margin: 5px;">'
text_area_html = '<br><textarea maxlength="1500" name="textinput1" class="textinput1" id="textinput1" placeholder="Please enter the output for the above commands here (Optional - max 1500 Chars)"></textarea>'
debug_start = '''
<span id="copyText" class=commandBox
      style="background-color:#f0f0f0; color:#333; padding:8px 12px; border-radius:6px; cursor:pointer; display:inline-block; font-family:monospace; text-align:start"
      onclick="copyToClipboard()">
<small>Click the debug box to copy the contents to Clipboard</small>
'''
debug_end = '''
</span>
<script>
  function copyToClipboard() {
    const text = document.getElementById('copyText').innerText;

    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        alert('Copied!');
      }).catch(err => {
        alert('Failed to copy: ' + err);
      });
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      alert('Copied!');
    }
  }
</script>
'''
# Troubleshooting steps with specific messages for 'Yes'/'No' responses
troubleshooting_steps = [

    {
        "step": "Sample step 1",
        "question": f'''
{dropdown("Sample dropdown", "This is a sample dropdown: ", ['Option1','Option2','Option3'])}

{checkbox_html} Sample checkbox: <a href="https://community.fortinet.com/t5/FortiGate/Technical-Tip-Allow-ping-from-a-specific-IP-for-administrative/ta-p/198040" target="_blank">Sample hyperlink</a>

Sample text input:
{text_area_html}

Sample debug commands:
{debug_start}
cli command 1
cli command 2
{debug_end}

Sanple inline input field {input_field('sample input field')}

What is the present status of the device? Select the option best applicable:

''',
        "info": "<li>info section text. info section text.</li> info section text. info section text. info section text. info section text. info section text. info section text.",
        "options": ["Step 2","Step 3 - non functional"],
        "next": {"Step 2": "Sample step 2"}
    },
    {
        "step": "Sample step 2",
        "question": f''' 

What happened leading up to the issue? Explain in as much detail as possible.
{text_area_html}

''',
        "info": "info section text",
        "options": ["Request Swarming"],
        "next": {"Request Swarming": "Troubleshooting Done"}
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
        
        input_values = {}
        # Collect all input fields from the form
        input_values = {}
        for key in request.form:
            if key not in ['choice', 'action', 'checkboxes', 'bypass_reason', 'textinput1']:
                value = request.form.get(key)
                if not value:
                    flash(f"Please fill in all required fields before proceeding.")
                    return redirect(url_for("troubleshoot"))
                try:
                    input_values[key] = str(value)
                except ValueError:
                    flash(f"Please enter a valid number for {key}", "error")
                    return redirect(url_for("troubleshoot"))
                
        step_report = f"Step {current_step+1}: {troubleshooting_steps[current_step]['step']} -> {choice}"
        if bypass_reason:
            step_report += f" (Bypassed with reason: {bypass_reason})"
        if textinput1:
            step_report += f"\n  Command output: \n{textinput1}\n\n"
        if input_values:
            for key, value in input_values.items():
                step_report += f"\n    - {key}: {value}"

        step_inputs = {}
        for field in troubleshooting_steps[current_step].get("input_fields", []):
            value = request.form.get(field)
            if not value:
                flash("Please fill in all required fields before proceeding.", "error")
                return redirect(url_for("troubleshoot"))
            step_inputs[field] = float(value)
        
        if step_inputs:
            step_report += f" -> Inputs: {step_inputs}"
        
        session.setdefault("report", []).append(step_report)
        session.setdefault("inputs", {}).update(step_inputs)

        #example of next step being decided based on comparitive analysis:
        if troubleshooting_steps[current_step]["step"] == "Comparison of speed tests":
            pc_download = session["inputs"].get(f"{Speed_test_1_download_name}", 0)


            pc_upload = session["inputs"].get(f"{Speed_test_1_upload_name}", 0)

            

            next_step = "Enable DTLS"
        else:
            next_step = troubleshooting_steps[current_step]["next"].get(choice, None)
        # end example

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
    input_fields = step_data.get("input_fields", [])
    info = step_data.get("info", "")

    return render_template("troubleshoot.html", question=session["current_question"], options=options, info=info, input_fields=input_fields, stored_inputs=session.get("inputs", {}), show_back=session.get("current_step", 0) > 0, messages=list(session.pop("_flashes", [])))

@app.route("/download_report")
def download_report():
    filename = f"troubleshooting_report_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    with open(filepath, "w") as f:
        f.write("\n".join(session.get("report", [])))
    
    return send_file(filepath, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8900)