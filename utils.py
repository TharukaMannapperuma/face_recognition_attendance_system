import mysql.connector

mysqldb = mysql.connector.connect(
    host="localhost", user="root", password="", database="python")  # established connection


def db_init():
    return mysqldb


def db_connect():
    mycursor = mysqldb.cursor()  # cursor() method create a cursor object
    return mycursor


def db_disconnect():
    mysqldb.close()  # Connection Close
