import json
import hashlib
import pymongo

db = pymongo.Connection().teamcode

salt = "&%*cas432(f^"
def gen_result(status,message,data=None):
	result = dict(
		status = status,
		message = message,
		data = data
		)
	return json.dumps(result)


def hash(password):
	return hashlib.md5(salt + password).hexdigest()

def get_attr(object):
	li = [item for item in dir(object) if item[0]!="_" ]
	#return dict(zip(li, li))
	return li

def get_submission_id():
	inc_submission_id()
	return db.data.find_one({"submission" : {"$gte":1}})["submission"]

def inc_submission_id():
	db.data.update({"submission" : {"$gte":1}},{"$inc":{ "submission":1}})