from __future__ import division
import pymongo
import fx
from bson.json_util import dumps 
import os
import zipfile
import datetime
import time
connection = pymongo.Connection()
db = connection.teamcode
problems_dir = "data/problems"
os.environ['TZ'] = 'Europe/Chisinau'

os.umask(0) 
class User(object):
    """ DB structure: name,email,pass,user_class """
    def __init__(self,email=None,password=None,name=None,user_class=0):
        self.name = name
        self.password = password
        self.email = email
        self.user_class = user_class

    def signup(self):
        if self.user_exists():
            return fx.gen_result("1","User exists")
        user = dict(
            name = self.name,
            password = fx.hash(self.password),
            email = self.email,
            user_class = self.user_class
            )
        db.users.insert(user)
        curr_dir = "data/users"+"/"+self.email+"/"
        try:
            os.mkdir(curr_dir)
        except OSError:
            pass
        return fx.gen_result("0","Signup Ok. Now you can <a href='#' onclick=\"show_box('login-box'); return false;\"> login.</a>")

    def authenticate(self):
        user = dict(
            email = str(self.email),
            password = fx.hash(self.password)
            )
        user = db.users.find_one(user)
        
        if not(user):
            return fx.gen_result("1","Failed")

        self.name = user["name"]
        self.email = user["email"]
        self.user_class = user["user_class"]
        data = dict(
            name = self.name,
            email = self.email,
            user_class = self.user_class 
            )
        return fx.gen_result("0", "Login ok",data)

    def user_exists(self):
        count = db.users.find({
            'email':self.email
            }).count()
        if count == 0:
            return False
        return True

    def get_user_info(self,email=None):
        if not email:
            email = self.email
        user = db.users.find_one({"email":email})
        return user

    def authorize(self,user_class):
        if self.user_class < user_class:
            return False
        return True

    def teacher(self,user):
        if self.user_class == 1:
            return True
        return False


class Problem(object):
    """ DB structure: name,author,timelimit,memorylimit,text,[testcases],type,source """
    def __init__(self,name,author,timelimit,memorylimit,text=None,testcases=None,validator=None,archive=False):
        self.name = name
        self.author = author
        self.timelimit = timelimit
        self.memorylimit = memorylimit
        self.text = text
        self.testcases = testcases
        self.validator = validator
        self.archive = archive

    def set_dir(self):
        curr_dir = problems_dir+"/"+self.name+"/"
        try:
            os.mkdir(curr_dir)
        except OSError:
            pass

    def exists(self):
        name = self.name
        n = db.problems.find({'name':name}).count()
        if n>0:
            return True
        return False

    def add(self):
        problem_data = dict(
            name = self.name,
            author = self.author,
            testcases = self.testcases,
            timelimit = self.timelimit,
            memorylimit = self.memorylimit,
            archive = self.archive
            )
        db.problems.insert(problem_data)
        return fx.gen_result("0","Problem added")

    def prepare_testcases(self):
        testcases = self.testcases
        name = self.name
        curr_dir = problems_dir+"/"+name
        f = open(curr_dir+"/testcases.zip","w")
        f.write(testcases)
        f.close()
        try:
            testcases = zipfile.ZipFile(curr_dir+'/testcases.zip','r')
        except:
            return {"status":"1","message":"Bad file"}
        
        files = testcases.namelist()
        if len(files) % 2 != 0:
            return {"status":"2","message":"Wrong number of files"}

        for i in xrange(1,int(len(files)/2)+1):
            if  not (str(i)+".in" in files) or not(str(i)+".ok" in files):
                return {"status":"3","message":"Wrong files"}

        testcases.extractall(curr_dir)
        for i in xrange(1,int(len(files)/2)+1):
            filename = curr_dir+"/"+str(i)+".in"
            text = open(filename, 'rb').read().replace('\r\n', '\n')
            open(filename, 'wb').write(text)
            filename = curr_dir+"/"+str(i)+".in"
            text = open(filename, 'rb').read().replace('\r\n', '\n')
            open(filename, 'wb').write(text)


        self.testcases = [0]*int((len(files)/2))
        return {"status":"0","message":"Message ok"}

    @staticmethod
    def count_submissions(name=None):
        if not name:
            name = self.name
        n = db.submissions.find({"problem":name}).count()
        return n



class Contest(object):
    """
    DB Structure: name,start,end,author,[problems], [enrolled]
    """
    def __init__(self,name=None,start=None,end=None,author=None,problems=None,enrolled=None):
        self.name = name
        self.start = start
        self.end = end
        self.author = author
        self.problems = problems
        enrolled = []

    def exists(self):
        n = db.contests.find({"name":self.name}).count()
        if n>0:
            return True
        return False

    def add(self):
        contest_data = dict(
            name = self.name,
            start = int(self.start),
            end = int(self.end),
            author = self.author,
            problems = self.problems,
            enrolled = []
            )
        db.contests.insert(contest_data)
        return fx.gen_result("0","Contest added")

    def get_active_contests(self):
        curr_time = time.time()
        contests = db.contests.find({
            "start" : { "$lte": curr_time },
            "end" : { "$gte" : curr_time }
            })
        print curr_time
        return list(contests)


class Submission(object):
    """
    DB Structure: user,problem,time,contest,lang,id,status,result,data
    """
    def __init__(self,user,problem,time,contest,lang,id,body,result=None,data=None):
        self.user = user
        self.problem = problem
        self.time = time
        self.contest = contest
        self.lang = lang
        self.id = id
        self.body = body
        self.status = "pending"

    def validate(self):
        body = self.body
        words = ["system","exec","shell"]
        for word in words:
            if word in body:
                return False
        return True

    def add(self):
        submission_data = dict(
            user = self.user,
            problem = self.problem,
            time = self.time,
            contest = self.contest,
            lang = self.lang,
            id = self.id,
            result  = None,
            data = None,
            status = self.status,
            score = 0
            )
        db.submissions.insert(submission_data)
        return {"status":"0","message":"Submission accepted"}

    @staticmethod
    def get_score(problem,user):
        submission = db.submissions.find_one({"user":user,"problem":problem},sort=[("time", pymongo.DESCENDING)])
        if not submission or not submission['data']:
            return 0

        n = len(submission['data'])
        r = 0
        for item in submission['data']:
            if item['status'] == '0':
                r +=1
        return int((r/n)*100)

    @staticmethod
    def get_submission_score(submission):
        submission = db.submissions.find_one({"id":submission})
        if not submission or not submission['data']:
            return 0

        n = len(submission['data'])
        r = 0
        for item in submission['data']:
            if item['status'] == '0':
                r +=1
        return int((r/n)*100)

class Clarification(object):
    """
    DB Structure: contest,text
    """
    def __init__(self,contest,text):
        self.contest = contest
        self.text = text

    def add(self):
        pass

    @staticmethod
    def get_clarifications(contests):
        li = []
        for contest in contests:
            li.append(contest["name"])
        clarifications = db.clarifications.find({"contest":{"$in":li}})
        return list(clarifications)