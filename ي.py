import os
import json
import cv2
import dlib
import sounddevice as sd
from scipy.io import wavfile as wav
import tkinter as tk
from tkinter import messagebox, Toplevel, simpledialog
from tkinter import ttk
import speech_recognition as sr
import pyttsx3
import numpy as np
import face_recognition
from datetime import datetime  # لاستيراد مكتبة التاريخ والوقت

# تعريف engine لاستخدامه في التعليق الصوتي
engine = pyttsx3.init()

# مسار ملف JSON لحفظ بيانات الطلاب
students_db_file = 'students_data.json'
assets_dir = 'assets'

# التأكد من وجود مجلد assets
if not os.path.exists(assets_dir):
    os.makedirs(assets_dir)


# تحميل البيانات من ملف JSON بشكل آمن
def load_students_data():
    if os.path.exists(students_db_file):
        try:
            with open(students_db_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            print("Error: The JSON file is corrupted or invalid.")
            return {}
    else:
        return {}


# حفظ البيانات في ملف JSON
def save_students_data(students_data):
    with open(students_db_file, 'w', encoding='utf-8') as file:
        json.dump(students_data, file, ensure_ascii=False, indent=4)


# فتح نافذة عرض الغياب
def open_sheet_window():
    # طلب كلمة مرور المسؤول
    admin_password = "admin123"  # كلمة السر الخاصة بعرض الحضور
    entered_password = tk.simpledialog.askstring("Password Required", "Enter Admin Password:", show="*")

    if entered_password != admin_password:
        messagebox.showerror("Access Denied", "Invalid password!")
        return

    sheet_window = Toplevel()
    sheet_window.title("Student Attendance Sheet")
    sheet_window.geometry("500x400")

    # تحميل بيانات الطلاب من ملف JSON
    students_data = load_students_data()

    # إنشاء جدول لعرض الأسماء والأرقام وحالة الحضور
    tree = ttk.Treeview(sheet_window, columns=("Student ID", "Name", "Attendance", "Time"), show="headings")
    tree.heading("Student ID", text="Student ID")
    tree.heading("Name", text="Name")
    tree.heading("Attendance", text="Attendance")
    tree.heading("Time", text="Time & Date")  # إضافة عمود الوقت والتاريخ

    # إضافة البيانات إلى الجدول
    for student_id, student in students_data.items():
        attendance_status = "Present" if student.get('present', False) else "Absent"
        time_date = student.get('attendance_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        tree.insert("", "end", values=(student_id, student['name'], attendance_status, time_date))

    # وضع الجدول داخل نافذة
    tree.pack(fill="both", expand=True)


# فتح نافذة تسجيل الطلاب
def open_register_window():
    register_window = tk.Toplevel()
    register_window.title("Register")
    register_window.geometry("400x400")

    tk.Label(register_window, text="اسم الطالب:").pack()
    name_entry = tk.Entry(register_window)
    name_entry.pack()

    tk.Label(register_window, text="رقم الطالب:").pack()
    student_id_entry = tk.Entry(register_window)
    student_id_entry.pack()

    tk.Label(register_window, text="كلمة السر:").pack()
    password_entry = tk.Entry(register_window, show="*")
    password_entry.pack()

    register_button = tk.Button(register_window, text="Take Face, Iris, and Voice Recognition",
                                command=lambda: register_student(name_entry.get(), student_id_entry.get(),
                                                                 password_entry.get()))
    register_button.pack()


# عملية التسجيل
def register_student(name, student_id, password):
    students_data = load_students_data()

    if student_id in students_data:
        messagebox.showerror("Error", f"Student with ID {student_id} is already registered!")
        return

    if name in [student['name'] for student in students_data.values()]:
        messagebox.showerror("Error", f"Student with name {name} is already registered!")
        return

    if name and student_id and password:
        messagebox.showinfo("Info", "Data received. Now taking face, iris, and voice recognition.")
        face_image_path = capture_face(student_id)
        iris_image_path = capture_iris(student_id)
        voice_sample = capture_voice_sample()
        if voice_sample:
            voice_file_path = os.path.join(assets_dir, f"{student_id}_voice.wav")
            with open(voice_file_path, 'w') as f:
                f.write(voice_sample)

        students_data[student_id] = {
            'name': name,
            'password': password,
            'face_data': face_image_path,
            'iris_data': iris_image_path,
            'voice_data': voice_sample,
            'present': False
        }

        save_students_data(students_data)
        messagebox.showinfo("Success", "Registration successful!")
    else:
        messagebox.showerror("Error", "Please fill in all fields.")


# التقاط بصمة الوجه
def capture_face(student_id):
    cap = cv2.VideoCapture(0)
    face_detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

    ret, frame = cap.read()
    if not ret:
        messagebox.showerror("Error", "Failed to capture face.")
        return None

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_detector(gray)

    for face in faces:
        x, y, w, h = (face.left(), face.top(), face.width(), face.height())
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    face_image_path = os.path.join(assets_dir, f"{student_id}_face.jpg")
    cv2.imwrite(face_image_path, frame)

    cap.release()
    cv2.destroyAllWindows()

    return face_image_path


# التقاط بصمة العين
def capture_iris(student_id):
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if not ret:
        messagebox.showerror("Error", "Failed to capture iris.")
        return None

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    eyes = eye_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    for (ex, ey, ew, eh) in eyes:
        cv2.rectangle(frame, (ex, ey), (ex + ew, ey + eh), (255, 0, 0), 2)

    iris_image_path = os.path.join(assets_dir, f"{student_id}_iris.jpg")
    cv2.imwrite(iris_image_path, frame)

    cap.release()

    return iris_image_path


# دالة تسجيل الصوت
def capture_voice_sample():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        engine.say("Please say a word to record your voice sample")
        engine.runAndWait()
        print("Please say a word...")
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            print("Voice sample recorded:", text)
            return text
        except sr.UnknownValueError:
            print("Sorry, I couldn't understand your speech.")
            return None
        except sr.RequestError:
            print("Could not request results; check your network connection.")
            return None


def compare_face_images(image1_path, image2_path):
    # تحميل الصور باستخدام face_recognition
    image1 = face_recognition.load_image_file(image1_path)
    image2 = face_recognition.load_image_file(image2_path)

    # استخراج الميزات من الصور
    encoding1 = face_recognition.face_encodings(image1)
    encoding2 = face_recognition.face_encodings(image2)

    if encoding1 and encoding2:
        # مقارنة الأنماط
        return face_recognition.compare_faces([encoding1[0]], encoding2[0])[0]
    return False

# التحقق من بصمة الوجه
def verify_face(student_id):
    students_data = load_students_data()
    student = students_data.get(student_id, {})
    if student:
        stored_face_path = student.get('face_data', "")
        if os.path.exists(stored_face_path):
            captured_face = capture_face(student_id)  # التقاط بصمة الوجه الجديدة
            if captured_face and compare_face_images(stored_face_path, captured_face):
                return True
    return False


# التحقق من بصمة العين (يتم استخدام مقارنة صور)
def verify_iris(student_id):
    # يمكن إضافة منطق التحقق لبصمة العين هنا
    students_data = load_students_data()
    student = students_data.get(student_id, {})
    if student:
        stored_iris_path = student.get('iris_data', "")
        if os.path.exists(stored_iris_path):
            captured_iris = capture_iris(student_id)  # التقاط بصمة العين الجديدة
            if captured_iris and compare_face_images(stored_iris_path, captured_iris):
                return True
    return False


# التحقق من بصمة الصوت
def verify_voice(student_id):
    # يمكن إضافة منطق التحقق لبصمة الصوت هنا
    students_data = load_students_data()
    student = students_data.get(student_id, {})
    if student:
        stored_voice = student.get('voice_data', "")
        if stored_voice:
            captured_voice = capture_voice_sample()  # تسجيل صوت جديد
            if captured_voice and stored_voice == captured_voice:
                return True
    return False


# فتح نافذة تسجيل الدخول
def open_login_window():
    login_window = Toplevel()
    login_window.title("Login")
    login_window.geometry("400x400")

    tk.Label(login_window, text="رقم الطالب:").pack()
    student_id_entry = tk.Entry(login_window)
    student_id_entry.pack()

    tk.Label(login_window, text="كلمة السر:").pack()
    password_entry = tk.Entry(login_window, show="*")
    password_entry.pack()

    login_button = tk.Button(login_window, text="Login", command=lambda: verify_student(student_id_entry.get(), password_entry.get()))
    login_button.pack()


def verify_student(student_id, password):
    students_data = load_students_data()

    student = students_data.get(student_id, {})

    if student and student.get('password') == password:
        # التحقق من بصمة الوجه
        if not verify_face(student_id):
            messagebox.showerror("Error", "Face verification failed!")
            return

        # التحقق من بصمة العين
        if not verify_iris(student_id):
            messagebox.showerror("Error", "Iris verification failed!")
            return

        # التحقق من بصمة الصوت
        if not verify_voice(student_id):
            messagebox.showerror("Error", "Voice verification failed!")
            return

        # إذا تم التحقق من جميع البصمات بنجاح
        student['present'] = True
        student['attendance_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # إضافة وقت وتاريخ الحضور
        students_data[student_id] = student  # تحديث بيانات الطالب في القاموس
        save_students_data(students_data)  # حفظ التحديثات في ملف JSON
        save_students_data(students_data)
        messagebox.showinfo("Success", f"Logged in successfully at {student['attendance_time']} and marked as present!")
    else:
        messagebox.showerror("Error", "Invalid student ID or password!")


# إعداد واجهة المستخدم
root = tk.Tk()
root.title("Student Biometric System")
root.geometry("300x250")

tk.Button(root, text="Register", command=open_register_window).pack(pady=10)
tk.Button(root, text="Login", command=open_login_window).pack(pady=10)
tk.Button(root, text="Attendance Sheet", command=open_sheet_window).pack(pady=10)

root.mainloop()
