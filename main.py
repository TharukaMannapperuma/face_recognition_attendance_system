import sys
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.uic import loadUi
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QDialog, QApplication, QMessageBox, QStackedWidget
import face_recognition
import picamera
import numpy as np
import pickle
from time import sleep
import os
from utils import db_init, db_connect
from PIL import Image, ImageDraw
from smbus2 import SMBus
from mlx90614 import MLX90614

facetrain = True
face_locations = []
face_locations_new = []
face_encodings = []
known_face_names = []
known_face_encodings = []
name = ''
login_temp = 0.0
register_screen_index = None
stop_flag = False
pickele_file = "dataset/dataset.pkl"

threshold_red = 37
threshold_start = 33


class face_recThread(QThread):

    name = ''
    changePixmap = pyqtSignal(QImage)
    stopped = pyqtSignal()

    def init_pkl(self):
        global known_face_names
        global known_face_encodings
        with open(pickele_file, 'rb') as f:
            all_face_encodings = pickle.load(f)
        known_face_names = list(all_face_encodings.keys())
        known_face_encodings = np.array(list(all_face_encodings.values()))

    def face_recognize(self, face_encodings):
        global name
        # Find all the faces and face encodings in the current frame of video
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(
                known_face_encodings, face_encoding)
            # # If a match was found in known_face_encodings, just use the first one.
            if True in matches:
                first_match_index = matches.index(True)
                name = str(known_face_names[first_match_index])
            else:
                name = "unknown"

    def run(self):
        global name
        condition = True
        self.init_pkl()
        sleep(2)
        process_this_frame = True
        camera = picamera.PiCamera()
        camera.resolution = (640, 480)
        frame = np.empty((240, 320, 3), dtype=np.uint8)
        while condition:
            global stop_flag
            print(stop_flag)
            if(stop_flag):
                break
            camera.capture(frame, format="rgb")
            frame = Image.fromarray(frame)
            rgb_small_frame = frame.resize((160, 120))
            print(rgb_small_frame.size)
            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            rgb_small_frame = np.array(rgb_small_frame)
            if process_this_frame:

                face_locations = face_recognition.face_locations(
                    rgb_small_frame)
                face_encodings = face_recognition.face_encodings(
                    rgb_small_frame, face_locations)
                self.face_recognize(face_encodings)
            process_this_frame = not process_this_frame
            try:
                # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                top = face_locations[0][0]*4
                right = face_locations[0][1]*4
                bottom = face_locations[0][2]*4
                left = face_locations[0][3]*4

                draw = ImageDraw.Draw(frame)
            # Draw a box around the face
                draw.rectangle(((left, top), (right, bottom)),
                               outline=(0, 0, 255))

# Draw a label with a name below the face
                text_width, text_height = draw.textsize(name)
                draw.rectangle(((left, bottom - text_height - 10),
                                (right, bottom)), fill=(0, 0, 255), outline=(0, 0, 255))
                draw.text((left + 6, bottom - text_height - 5),
                          name, fill=(255, 255, 255, 255))

                del draw
                print("Name is: ", name)
                if name == "unknown":
                    print("Unknown")
                    condition = False
                elif len(name) != 0:
                    print("Known")
                    condition = False
            except:
                print("No Face Data")
            frame = np.array(frame)
            rgbImage = frame
            h, w, ch = rgbImage.shape
            bytesPerLine = ch * w
            convertToQtFormat = QImage(
                rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
            p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
            self.changePixmap.emit(p)
        print("While END")
        self.stopped.emit()


class face_addThread(QThread):

    stopped = pyqtSignal()

    def __init__(self, user_id, parent=None):
        super(face_addThread, self).__init__()
        self.user_id = user_id
        print(self.user_id)
        self.run()

    def run(self):
        global known_face_encodings
        global facetrain
        print("Trining and Generating Pickle File")
        try:
            known_image = face_recognition.load_image_file(
                str(self.user_id)+".jpg")
            face_locations = face_recognition.face_locations(known_image)
            known_image_encoding = face_recognition.face_encodings(
                known_image, face_locations)[0]
            objects = []
            with (open(pickele_file, "rb")) as openfile:
                while True:
                    try:
                        objects.append(pickle.load(openfile))
                    except EOFError:
                        break
            objects[0][self.user_id] = known_image_encoding
            with open(pickele_file, 'wb') as f:
                pickle.dump(objects[0], f)
            print("Done!")
            self.stopped.emit()

        except IndexError:
            print("Face is not clear")
            facetrain = False
            self.stopped.emit()


class get_tempThread(QThread):

    tempe = pyqtSignal(float)
    stopped = pyqtSignal()

    def run(self):
        self.bus = SMBus(1)
        self.sensor = MLX90614(self.bus, address=0x5A)
        self.temp = 0
        while (True):
            if (self.temp > threshold_start):
                self.bus.close()
                break
            self.temp = self.sensor.get_object_1()
            self.temp = round(self.temp, 2)
            self.tempe.emit(self.temp)
            print(self.temp)
        print("Loop Broke")
        self.stopped.emit()


class photoThread(QThread):

    changePixmap = pyqtSignal(QImage)
    stopped = pyqtSignal()
    saveimage = pyqtSignal(object)

    def init_pkl(self):
        global known_face_names
        global known_face_encodings
        with open(pickele_file, 'rb') as f:
            all_face_encodings = pickle.load(f)
        known_face_names = list(all_face_encodings.keys())
        known_face_encodings = np.array(list(all_face_encodings.values()))

    def face_recognize(self, face_encodings):
        global name
        name = ''
        # Find all the faces and face encodings in the current frame of video
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(
                known_face_encodings, face_encoding)
            # # If a match was found in known_face_encodings, just use the first one.
            if True in matches:
                first_match_index = matches.index(True)
                name = str(known_face_names[first_match_index])
            else:
                name = "unknown"

    def run(self):
        global name
        global face_locations_new
        condition = True
        self.init_pkl()
        process_this_frame = True
        camera = picamera.PiCamera()
        camera.resolution = (640, 480)
        frame = np.empty((240, 320, 3), dtype=np.uint8)
        while condition:
            camera.capture(frame, format="rgb")
            frame = Image.fromarray(frame)
            rgb_small_frame = frame.resize((160, 120))
            print(rgb_small_frame.size)
            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            rgb_small_frame = np.array(rgb_small_frame)
            if process_this_frame:

                face_locations = face_recognition.face_locations(
                    rgb_small_frame)
                face_locations_new = face_locations
                face_encodings = face_recognition.face_encodings(
                    rgb_small_frame, face_locations)
                self.face_recognize(face_encodings)
            process_this_frame = not process_this_frame
            frame = np.array(frame)
            try:
                print("Name is: ", name)
                self.saveimage.emit(frame)
                if name == "unknown":
                    print("Unknown")
                    condition = False
                elif len(name) != 0:
                    print("Known")
                    condition = False
            except:
                print("No Face Data")
            rgbImage = frame
            h, w, ch = rgbImage.shape
            bytesPerLine = ch * w
            convertToQtFormat = QImage(
                rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
            p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
            self.changePixmap.emit(p)

        sleep(3)
        self.stopped.emit()


class WelcomeScreen(QDialog):

    def __init__(self):
        super(WelcomeScreen, self).__init__()
        loadUi('ui/welcome.ui', self)
        self.initUI()
        self.temp = 0
        print(self.temp)

    def gotoLogin(self):
        old_temp = self.temp
        self.temp = 0
        self.login = LoginScreen(old_temp)
        widget.addWidget(self.login)
        print(widget.currentIndex())
        widget.removeWidget(widget.currentWidget())
        widget.setCurrentIndex(widget.currentIndex()+1)

    @ pyqtSlot(float)
    def setTemp(self, temp):
        self.temp = temp
        if(self.temp > threshold_red):
            self.templabel.setStyleSheet(
                "color:red; font: 100 26pt 'Segoe UI Black';")
        else:
            self.templabel.setStyleSheet(
                "color:white; font: 100 26pt 'Segoe UI Black';")
        self.templabel.setText(str(self.temp)+"C")
        print("Set Temp: ", self.temp)

    def initUI(self):
        # create a label
        self.tempthread = get_tempThread(self)
        self.tempthread.stopped.connect(self.tempthread.quit)
        self.tempthread.stopped.connect(self.threadStopped)
        self.tempthread.tempe.connect(self.setTemp)
        self.tempthread.start()
        self.show()

    def threadStopped(self):
        print("Stopped")
        self.gotoLogin()


class RegisterScreen(QDialog):

    global register_screen_index

    def __init__(self, temp):
        super(RegisterScreen, self).__init__()
        loadUi('ui/register.ui', self)
        self.temp = temp
        print(self.temp)
        if(self.temp > threshold_red):
            self.templcd.setStyleSheet(
                "color:red; font: 100 26pt 'Segoe UI Black';")
        else:
            self.templcd.setStyleSheet(
                "color:white; font: 100 26pt 'Segoe UI Black';")
        self.templcd.display(self.temp)
        self.registernxt.clicked.connect(self.registerFunction)
        self.idlogin.clicked.connect(self.gotoIdlogin)
        self.gohome.clicked.connect(self.gotoHome)

    def gotoHome(self):
        self.welcome = WelcomeScreen()
        widget.addWidget(self.welcome)
        widget.removeWidget(widget.currentWidget())
        widget.setCurrentIndex(0)

    def gotoIdlogin(self):
        self.idlogin = IdloginScreen(self.temp)
        widget.addWidget(self.idlogin)
        widget.removeWidget(widget.currentWidget())
        widget.setCurrentIndex(widget.currentIndex()+1)

    def registerFunction(self):
        reg_name = self.nameinput.text()
        userId = self.idinput.text()
        role = self.roleinput.text()
        # print(reg_name, userId, role, self.temp)
        data_list = [reg_name, userId, role, self.temp]
        self.gotoRegisterPhoto(data_list)

    def gotoRegisterPhoto(self, data_list):
        self.photo = RegisterPhoto(data_list)
        widget.addWidget(self.photo)
        widget.removeWidget(widget.currentWidget())
        widget.setCurrentIndex(widget.currentIndex()+1)


class RegisterPhoto(QDialog):
    global register_screen_index

    def __init__(self, data_list):
        super(RegisterPhoto, self).__init__()
        loadUi('ui/photo.ui', self)
        self.data_list = data_list
        print(data_list)
        self.facesave = True
        self.initUI()

    @ pyqtSlot(QImage)
    def setImage(self, image):
        self.photo.setPixmap(QPixmap.fromImage(image))
        self.image = image

    def initUI(self):
        # create a label
        th = photoThread(self)
        th.changePixmap.connect(self.setImage)
        th.stopped.connect(th.quit)
        th.stopped.connect(self.threadStopped)
        th.saveimage.connect(self.setSaveImage)
        th.start()
        self.show()

    def setSaveImage(self, saveimage):
        self.saveimage = saveimage

    def threadStopped(self):
        print("Stopped")
        self.gotoFinish(self.data_list)

    def convertToBinaryData(self, filename):
        with open(filename, 'rb') as file:
            binaryData = file.read()
        return binaryData

    def gotoRegister(self):
        widget.removeWidget(widget.currentWidget())
        self.register = RegisterScreen()
        widget.addWidget(self.register)
        print("Index = ", register_screen_index)
        widget.setCurrentIndex(widget.currentIndex()+1)

    def gotoFinish(self, data_list):
        global facetrain
        try:
            self.mycursor = db_connect()  # cursor() method create a cursor object
            self.mycursor.execute(
                "SELECT id FROM users ORDER BY id DESC LIMIT 1;")
            self.result = self.mycursor.fetchall()  # fetches all the rows in a result set
            if (len(self.result) == 0):
                self.img_id = 1
            else:
                self.img_id = self.result[0][0]+1

            print(face_locations_new)
            top, right, bottom, left = face_locations_new[0]
            face_image = self.saveimage[(top*4) - 100:(bottom*4) +
                                        100, (left*4)-100:(right*4)+100]
            face_image = face_image[:, :, ::-1]
            Image.fromarray(face_image).save("{}.jpg".format(self.img_id))
            print("Image Saved\n")
            print(data_list)
            sql_insert_blob_query = """ INSERT INTO users(name,user_id,role,temp,photo) VALUES (%s,%s,%s,%s,%s)"""
            insert_blob_tuple = (data_list[0], data_list[1], data_list[2],
                                 data_list[3], self.convertToBinaryData("{}.jpg".format(self.img_id)))
            savep = face_addThread(self.img_id, self)
            savep.stopped.connect(savep.quit)
            print("Inside Finish = ", self.facesave)
            if(facetrain):
                result = self.mycursor.execute(
                    sql_insert_blob_query, insert_blob_tuple)
                db_init().commit()  # Commit is used for your changes in the database
                print(
                    "Image and data inserted successfully as a BLOB into python_employee table", result)
                print("\nRegistration Success")
                os.remove("{}.jpg".format(self.img_id))
                widget.removeWidget(widget.currentWidget())
                self.welcome = WelcomeScreen()
                widget.addWidget(self.welcome)
                widget.setCurrentIndex(0)
            else:
                print("Registration Failed!")
                print("Try Registering Again 1!")
                self.gotoRegister()

        except Exception as e:
            print("Error Occured: ", e)
            print("Registration Failed!")
            print("Try Registering Again!")
            self.gotoRegister()


class LoginScreen(QDialog):
    global name

    def __init__(self, temperature):
        super(LoginScreen, self).__init__()
        loadUi('ui/login.ui', self)
        self.initUI()
        self.temp = temperature
        print(self.temp)
        self.idlogin.clicked.connect(self.gotoIdlogin)

    @ pyqtSlot(QImage)
    def setImage(self, image):
        self.width = self.image.width()
        self.height = self.image.height()
        self.image.setPixmap(QPixmap.fromImage(
            image).scaled(self.width, self.height))

    def initUI(self):
        # create a label
        self.th = face_recThread(self)
        self.th.changePixmap.connect(self.setImage)
        self.th.stopped.connect(self.th.quit)
        self.th.stopped.connect(self.threadStopped)
        self.th.start()
        self.show()

    def gotoIdlogin(self):
        if(self.th.isRunning()):
            global stop_flag
            stop_flag = True
        print("Thread Stopped!")
        self.idlogin = IdloginScreen(self.temp)
        widget.addWidget(self.idlogin)
        widget.removeWidget(widget.currentWidget())
        widget.setCurrentIndex(widget.currentIndex()+1)

    def threadStopped(self):
        print("Stopped")
        global stop_flag
        print(stop_flag)
        if (name == "unknown" and (not stop_flag)):
            print("Unkown Name Please Register or Enter Your ID to enter")
            self.gotoRegister()
        elif(name == "0" and (not stop_flag)):
            print("Unkown Name Please Register or Enter Your ID to enter")
            self.gotoRegister()
        elif(len(name) != 0 and (not stop_flag)):
            self.gottoDetails(name)
        stop_flag = False
        print(stop_flag)

    def gottoDetails(self, name):
        user_id = int(name)
        self.query = "SELECT * FROM users WHERE id='{}'".format(user_id)
        self.mycursor = db_connect()
        self.mycursor.execute(self.query)
        self.result = self.mycursor.fetchall()
        self.result = list(self.result[0])
        self.result[4] = self.temp
        self.details = DetailsScreen(self.result[0:-1])
        widget.addWidget(self.details)
        widget.removeWidget(widget.currentWidget())
        widget.setCurrentIndex(widget.currentIndex()+1)

    def gotoRegister(self):
        self.register = RegisterScreen(self.temp)
        widget.addWidget(self.register)
        print("Index = ", register_screen_index)
        widget.removeWidget(widget.currentWidget())
        widget.setCurrentIndex(widget.currentIndex()+1)


class DetailsScreen(QDialog):
    def __init__(self, data_array):
        super(DetailsScreen, self).__init__()
        loadUi('ui/details.ui', self)
        self.data_array = data_array
        # print(data_array)
        self.write_file(self.data_array[-1], str(self.data_array[0])+".jpg")
        self.width = self.photo.width()
        self.height = self.photo.height()
        self.photo.setPixmap(QPixmap(
            str(self.data_array[0])+".jpg").scaled(self.width, self.height))
        self.finish.clicked.connect(self.goHome)
        self.name.setText(str(self.data_array[1]))
        self.id.setText(str(self.data_array[2]))
        self.role.setText(str(self.data_array[3]))
        os.remove("{}.jpg".format(str(self.data_array[0])))
        if(int(self.data_array[4]) > threshold_red):
            self.temp.setStyleSheet(
                "color:red; font: 100 26pt 'Segoe UI Black';")
        else:
            self.temp.setStyleSheet(
                "color:white; font: 100 26pt 'Segoe UI Black';")
        self.temp.setText(str(self.data_array[4])+" C")
        sql_insert = """ INSERT INTO logs(user_id,temp) VALUES (%s,%s)"""
        insert_tuple = (str(self.data_array[2]), str(self.data_array[4]))
        self.mycursor = db_connect()
        result = self.mycursor.execute(
            sql_insert, insert_tuple)
        db_init().commit()  # Commit is used for your changes in the database
        print(
            "Login logged in database", result)
        print("\nData Logged!")

    def goHome(self):
        self.welcome = WelcomeScreen()
        widget.addWidget(self.welcome)
        widget.removeWidget(widget.currentWidget())
        widget.setCurrentIndex(0)

    def write_file(self, data, filename):
        # Convert binary data to proper format and write it on Hard Disk
        with open(filename, 'wb') as file:
            file.write(data)


class IdloginScreen(QDialog):
    def __init__(self, temperature):
        super(IdloginScreen, self).__init__()
        loadUi('ui/idlogin.ui', self)
        self.temp = temperature
        self.login.clicked.connect(self.loginFunction)

    def loginFunction(self):
        user_id = self.user_id.text()
        self.query = "SELECT * FROM users WHERE user_id='{}'".format(user_id)
        self.mycursor = db_connect()
        self.mycursor.execute(self.query)
        self.result = self.mycursor.fetchall()
        self.result = list(self.result[0])
        self.result[4] = self.temp
        self.register = DetailsScreen(self.result[0:-1])
        widget.addWidget(self.register)
        widget.removeWidget(widget.currentWidget())
        widget.setCurrentIndex(widget.currentIndex()+1)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    welcome = WelcomeScreen()
    widget = QStackedWidget()
    widget.addWidget(welcome)
    widget.setFixedWidth(960)
    widget.setFixedHeight(720)
    widget.show()
    sys.exit(app.exec())
