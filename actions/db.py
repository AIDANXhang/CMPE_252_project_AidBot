import mysql.connector

def data_store(categories, location, response):
    mydb = mysql.connector.connect(
        host = "localhost",
        user = "root",
        passwd = "root",
        database = "aidbot"
    )

    mycursor = mydb.cursor()
    sql_cmd = 'INSERT INTO aidbot_table (categories, location, response) VALUES ("{0}","{1}","{2}");'.format(categories, location, response)
    mycursor.execute(sql_cmd)
    mydb.commit()

if __name__=="__main__":
    data_store("dentist", "testloc2", "testresp2")
