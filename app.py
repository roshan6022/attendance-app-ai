from flask import Flask, render_template, request, send_file, redirect
import pandas as pd
import pytesseract
from PIL import Image
import io
import os
import re
from datetime import datetime

app = Flask(__name__)

attendance_df = pd.DataFrame(columns=["Name", "Status", "Date"])

# If Tesseract is not in PATH:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

@app.route('/')
def index():
    return render_template('index.html', attendance=attendance_df.to_dict(orient='records'))

@app.route('/submit_manual', methods=['POST'])
def submit_manual():
    global attendance_df
    names = request.form.getlist('name')
    statuses = request.form.getlist('status')
    date = request.form.get('manual_date')

    for name, status in zip(names, statuses):
        if name.strip():
            attendance_df = attendance_df._append({
                "Name": name.strip(),
                "Status": status,
                "Date": date
            }, ignore_index=True)

    return redirect('/')

@app.route('/upload_image', methods=['POST'])
def upload_image():
    global attendance_df

    file = request.files['image']
    if file:
        image = Image.open(file.stream)
        text = pytesseract.image_to_string(image)

        # Extract date (e.g., "Attendance - April 5")
        date_match = re.search(r'Attendance\s*-\s*(\w+\s+\d+)', text)
        if date_match:
            try:
                date_obj = datetime.strptime(date_match.group(1), '%B %d')
                date = date_obj.replace(year=datetime.now().year).strftime('%Y-%m-%d')
            except:
                date = datetime.now().strftime('%Y-%m-%d')
        else:
            date = datetime.now().strftime('%Y-%m-%d')

        # Extract absent names after "Absent:"
        names = []
        if "Absent:" in text:
            lines = text.splitlines()
            index = next((i for i, line in enumerate(lines) if "Absent" in line), -1)
            if index != -1:
                for line in lines[index + 1:]:
                    line = line.strip()
                    if line and not line.lower().startswith("present"):
                        names.append(line)

        for name in names:
            attendance_df = attendance_df._append({
                "Name": name.strip(),
                "Status": "Absent",
                "Date": date
            }, ignore_index=True)

    return redirect('/')

@app.route('/delete_attendance', methods=['POST'])
def delete_attendance():
    global attendance_df
    name = request.form['name']
    date = request.form['date']

    attendance_df = attendance_df[
        ~((attendance_df['Name'] == name) & (attendance_df['Date'] == date))
    ]

    return redirect('/')

@app.route('/download')
def download():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        attendance_df.to_excel(writer, index=False, sheet_name='Attendance')
    output.seek(0)
    return send_file(output, download_name="attendance.xlsx", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)