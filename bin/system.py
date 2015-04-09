#!/usr/bin/env python
import pymongo
import time
import shutil
from subprocess import Popen,PIPE
import os
import filecmp
import pprint
import sys
import sys, time
from daemon import Daemon
import json

import itertools
import mimetools
import mimetypes
from cStringIO import StringIO
import httplib
import urllib, urllib2
import base64

from Crypto.Cipher import XOR



db = pymongo.Connection().teamcode

judgehosts = [
    dict(
        name = "JudgeHost1",
        address = "107.170.181.32",
        port = 8080
        )
]


key = "gyfjksdj156jknlmvc"

def gen_result(status,message,runtime,score,example=False):
    data = dict(
        status = status,
        message = message,
        score = score,
        runtime = runtime
        )
    return data

def submit(id,result,data=None):
    score = 0
    if not (type(result) is list):
        result = [result]
        print result
    if data:
        for test in data:
            score += int(test['score'])
    db.submissions.update({"id":id},{
        "$set":{"result":result,"data":data,"status":"done","score":score}
        })
    print result

def clean():
    #line = sys.stdin.readline()
    Popen(["bash","clean.sh"]).wait()

def encode(plaintext, key):
  cipher = XOR.new(key)
  return base64.b64encode(cipher.encrypt(plaintext))

def decode(ciphertext, key):
  cipher = XOR.new(key)
  return cipher.decrypt(base64.b64decode(ciphertext))

def prepare_params(params):
    string = ""
    for key,value in params.iteritems():
        string += "%s=%s&" % (key,value)
    string = string[:-1]
    return string

def evaluator():
    while True:
        data = []
        result_data = []
        #Get pending submission
        submission = db.submissions.find_and_modify({"status":"pending"},
                                                    {"$set":{"status":"evaluating"}},
                                                    sort=[('time',pymongo.ASCENDING)],)
        if not submission:
            time.sleep(3)
            continue

        """
        judgehost = judgehosts[0]

        #Check for problem existence

        data = dict(
            problem_id = problem_id,
            name = problem["name"]
            )

        params = encode(prepare_params(data),key)
        headers = {'Content-Type': 'plain/text'}
        conn = httplib.HTTPConnection(judgehost["address"],judgehost["port"])
        try:
            conn.request("POST","/problem/check",params,headers)
            response = conn.getresponse()
            data = response.read()
            conn.close()
        except:
            e = sys.exc_info()[0] 
            print "Error: %s" % e
            continue

        data = json.loads(decode(data,key))
        print data

        #Add problem
        if data["status"] == "2":
            problem["_id"] = problem_id
            file_data = open("../data/problems/%s/testcases.zip" % problem["name"],"rb").read()
            data = dict(
                testcases = base64.b64encode(file_data),
                name = problem["name"],
                id = problem_id,
                memorylimit = problem["memorylimit"],
                testcases_data = json.dumps(problem["testcases"]),
                timelimit = problem["timelimit"]
                )


            params = encode(prepare_params(data),key)
            headers = {'Content-Type': 'plain/text'}

            conn = httplib.HTTPConnection(judgehost["address"],judgehost["port"])
            conn.request("POST","/problem/add",params,headers)
            response = conn.getresponse().read()
            data = json.loads(decode(response,key))
            print data

        #Send submission



        continue

        """
        id = int(submission["id"])
        lang = submission["lang"]
        problem = submission["problem"]
        user = submission["user"]
        print "Evaluating sumbission: %s, problem: %s, user: %s" % (id,problem,user['email'])

        #Get problem
        problem = db.problems.find_one({"name":problem})
        memorylimit = problem["memorylimit"]
        timelimit = float(problem["timelimit"])

        #db.submissions.update({"id":id},{"$set":{"status":"evaluating"}})

        #Copy source
        shutil.copy("../data/users/"+user["email"]+"/"+str(id)+"."+lang, "tmp/file."+lang)

        #Compile
        process = Popen(["bash","compile.sh",submission['lang']],stdout=PIPE)
        exit_code = os.waitpid(process.pid, 0)
        output = process.communicate()[0]
        #time.sleep(40)
        #break
        if not os.path.isfile("tmp/file"):
            result = gen_result("1","Compile error",0,0)
            submit(id,result)
            continue
        
        #Loop testcases
        i = 0
        for testcase in problem["testcases"]:
            i += 1
            testcase = int(testcase)
            #Get info
            example = "yes"
            if testcase:
                example = False
            #Copy Input
            shutil.copy("../data/problems/"+problem['name']+"/"+str(i)+".in", "tmp/"+problem['name']+".in")

            #Run script
            time_limit = int(float(timelimit)+1)
            start = time.time()
            process = Popen(["bash","run.sh",str(time_limit),str(int(memorylimit)*1024),"file"], stdout=PIPE,stderr=PIPE)
            out, err = process.communicate()
            end = time.time()
            runtime = end-start
            
            #Check for memory limit

            if err:
                result = gen_result("2","Memory limit exceeded",runtime,0,example)
                data.append(result)
                if example:
                    result_data.append(result)
                clean()
                continue

            print "Runtime: "+str(runtime)+"s"
            #Check for timelimit
            if runtime > timelimit:
                result = gen_result("3","Timelimit exceeded",runtime,0,example)
                data.append(result)
                if example:
                    result_data.append(result)
                clean()
                continue

            #Check for Output
            if not os.path.isfile("tmp/"+problem['name']+'.out'):
                result = gen_result("4","No output file",runtime,0,example)
                data.append(result)
                if example:
                    result_data.append(result)
                clean()
                continue

            #Copy Ok file
            shutil.copy("../data/problems/"+problem['name']+"/"+str(i)+".ok", "tmp/"+problem['name']+".ok")

            #Compare files
            """with open("tmp/"+problem['name']+".out", 'r') as fin:
                print fin.read()

            with open("tmp/"+problem['name']+".ok", 'r') as fin:
                print fin.read()
            """
            trim1 = Popen(["bash","trim.sh",problem['name']+".ok",problem['name']+".out"],stderr = PIPE,stdout=PIPE)
            out, err = trim1.communicate()

            f = open("tmp/"+problem['name']+".ok", 'r').read()
            g = open("tmp/"+problem['name']+".out", 'r').read()
            print "Testcase: "+str(i)
            print "Out: "+g
            print "Ok: "+f
            print "\n"
            #sys.exit()
            #if not filecmp.cmp("tmp/"+problem['name']+".ok", "tmp/"+problem['name']+".out"):
            if f != g:
                result = gen_result("5","Wrong answer",runtime,0,example)
                data.append(result)
                if example:
                    result_data.append(result)
                clean()
                continue
            result = gen_result("0","Correct",runtime,testcase,example)
            data.append(result)
            if example:
                result_data.append(result)
            clean()


        #Clean folder
        process = Popen(["bash","clear.sh"],stderr = PIPE)
        
        #Submit
        #pprint.pprint(data)
        submit(id,result_data,data)
        err = process.communicate()
        
        time.sleep(3)




if __name__ == "__main__":
    evaluator()