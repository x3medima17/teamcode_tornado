import pymongo
from pprint import pprint



db = pymongo.Connection().teamcode


contests = ["Colegii Mari","Colegii Mici"]
data =  db.submissions.aggregate(
	[
		{ 
			"$sort":{
					"date":1,"user":1, "score":1
			}
		}, 
		{ 
			"$group" : { 
				"_id": "$user", 
				"lastSubmission": {
					"$last": "$time"
				},
				"contest" :{
					"$first":"$contest"
				}, 
				"score": {
					"$first":"$score"
				},
				"data":{
					"$first":"$data"
				},
				"problem":{
					"$first":"$problem"
				},
				"result":{
					"$first": "$result"
				},

			} 
		} 
	])

f = open("result.dat","w")
for item in data['result']:
	pprint(item)
	f.write("Name: %s,  contest: %s,  problem: %s,  score: %s\nExample result:\n" % (item["_id"]["name"],item["contest"],item["problem"],item["score"])) 
	for testcase in item["result"]:
		runtime = round(testcase["runtime"],3)
		f.write("status: %s,  runtime: %s,  message: %s,  score: %s\n" % (testcase["status"],runtime,testcase["message"],testcase["score"]))
	if not item["data"]:
		f.write("\n")
		continue
	f.write("Testcases result:\n")	
	for testcase in item["data"]:
		runtime = round(testcase["runtime"],3)
		f.write("status: %s,  runtime: %s,  message: %s,  score: %s\n" % (testcase["status"],runtime,testcase["message"],testcase["score"]))

	f.write("\n\n")




# pprint(data[0])
