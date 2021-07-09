import mysql.connector

mysqldb = mysql.connector.connect(
    host="localhost", user="root", password="", database="python")
try:
    mycursor = mysqldb.cursor()

    table = []
    table.append(""" CREATE TABLE IF NOT EXISTS `logs` (
  `id` int(100) NOT NULL AUTO_INCREMENT,
  `user_id` varchar(100) NOT NULL,
  `temp` varchar(10) NOT NULL,
  `logged_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8; """)

    table.append("""CREATE TABLE IF NOT EXISTS `users` (
  `id` int(100) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `user_id` varchar(100) NOT NULL,
  `role` varchar(100) NOT NULL,
  `temp` varchar(100) NOT NULL,
  `photo` longblob,
  `reg_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;""")
    for query in table:
        mycursor.execute(query)
        print("Success!")
except Exception as e:
    print("Error", e)
mysqldb.close()
