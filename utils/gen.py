import sys
import string
import random
sys.path.insert(0,"../")
import models
import json

def gen():
	lst = [random.choice(string.ascii_letters + string.digits) for n in xrange(8)]
	str = "".join(lst)
	return str

f = open("users.json","r").readlines()

users = []
for item in f:
	item = item.split(',')
	password = gen()
	user_data = dict(
		name = item[0],
		email = item[1],
		password = item[2].replace("\r\n","")
		)

	users.append(user_data)
	user = models.User(**user_data)
	result = user.signup()
	print result

users = json.dumps(users)
f = open("users_data.json","w")
f.write(users)
f.close()
print users
