#!/usr/bin/env python
import tornado.web
import tornado.ioloop
import tornado.httpserver
import os
import fx 
import models
import json
import pymongo
import tornado.options
from tornado.options import define,options
from  pprint import pprint
import urllib
import datetime
from bson.json_util import dumps
from time import time as now
import copy
import sys, time
from daemon import Daemon

define("port",default=80,help="Service port",type=int)
options.parse_command_line()

db = pymongo.Connection().teamcode
os.environ['TZ'] = 'Europe/Chisinau'
SERVER_ON = True
ips = ["37.233.52.133","188.131.57.151","77.89.198.130","188.131.43.204","94.243.125.16"]

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/",MainHandler),
            (r"/home",HomeHandler),


            (r"/contests",Contests.ContestsHandler),

            (r"/problems",Problems.ProblemsHandler),

            (r"/testcases",Testcases.TestcasesHandler),
            (r"/testcases/set",Testcases.TestcaseSetHandler),
            (r"/testcases/download", Testcases.TestcaseDownloadHandler),

            (r"/submission",Submission.SumbissionHandler),
            (r"/submissions",Submission.SubmissionViewHandler),
            (r"/submission/rejudge",Submission.SubmissionRejudgeHandler),
           
            (r"/scoreboard",Scoreboard.ScoreoardHandler),
            (r"/scoreboard/export",Scoreboard.ScoreboardExportHandler),

            (r"/archive",Archive.ArchiveHandler),
            (r"/archive/submissions",Archive.ArchiveViewHandler),

            (r"/clarifications",Claifications.ClarificationsHandler),

            (r"/auth",Auth.AuthHandler),
            (r"/auth/signup",Auth.SignupHandler),
            (r"/auth/login",Auth.LoginHandler),
            (r"/logout",Auth.LogoutHandler)
               
        ]
        
        settings = dict(
            debug = True,
            template_path = os.path.join(os.path.dirname(__file__),"templates"),
            static_path = os.path.join(os.path.dirname(__file__),"static"),
            login_url = "/auth",
            cookie_secret = "Settings.COOKIE_SECRET",
            
        )
        tornado.web.Application.__init__(self,handlers,**settings)


class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        user_json = self.get_secure_cookie("user")
        if not user_json: return None
        data = json.loads(user_json)
        pprint(data)
        user = db.users.find_one({"email":data["email"]})
        del user["_id"]
        if not user:
            self.set_status(401)
            self.finish("Unauthorized")
            return

        return user

    def prepare(self):
        req = self.request
        ip = req.remote_ip
        if ip in ips:
            self.set_status(401)
            self.finish("Unauthorized")
            return
        user = self.current_user
        data = dict(
            uri = req.uri,
            path = req.path,
            query = req.query,
            version = req.version,
            headers = req.headers,
            body = req.body,
            method = req.method,
            cookies = req.cookies,
            protocol = req.protocol,
            remote_ip = req.remote_ip 
            )
        if user:
            data["user"] = user
        #db.log.insert(data)
        if not SERVER_ON and user and user['email'] != "dimasavva17@gmail.com":
            self.clear()
            self.set_status(400)
            self.finish("Server under maintenance <a href='/logout'>Logout</a>")
    	os.umask(0)

        body = self.request.body
        #pprint(body)


class MainHandler(BaseHandler,tornado.web.RequestHandler):
    def get(self):
        self.redirect("/home")


class HomeHandler(BaseHandler,tornado.web.RequestHandler):
    @tornado.web.authenticated
    def get(self):
        user = models.User(**self.current_user)
        user_data = user.get_user_info()
        contests = models.Contest().get_active_contests()
        submissions = db.submissions.find({"user.email":self.current_user['email']}).sort("time",-1)
        page_data = dict(
            title = "Home",
            user = user_data,
            contests = list(contests),
            submissions = list(submissions)
            )
        self.render("index.html",**page_data)


class Claifications():
    class ClarificationsHandler(BaseHandler,tornado.web.RequestHandler):
        def put(self):
            clarifications = db.clarifications.find()
            clarifications = list(clarifications)
            print clarifications
            self.write(dumps(clarifications))


class Archive():
    class ArchiveHandler(BaseHandler,tornado.web.RequestHandler):
        @tornado.web.authenticated
        def get(self):
            user = models.User(**self.current_user)
            user_data = user.get_user_info()
            problems = list(db.problems.find({"archive":True}).sort("_id",-1))
            for i in xrange(len(problems)):
                problems[i]["submissions"] = models.Problem.count_submissions(name=problems[i]["name"])
                problems[i]["score"] = str(models.Submission.get_score(problem=problems[i]["name"],user=self.current_user))+"%"
                
            page_data = dict(
                title = "Home",
                user = user_data,
                problems = problems
            )
            self.render("archive.html",**page_data)

        @tornado.web.authenticated
        def post(self):
            user = self.current_user
            if user["user_class"] < 1:
                return

            problem = self.get_argument("problem",None)
            if not problem:
                self.write(fx.gen_result("1","Missing data"))
                return

            cursor  = db.problems.find({"problem":{"$in":[problem]},"end":{"$lt":now()}})
            print list(cursor)
            n = None
            #n = cursor.count()
            if n:
                self.write(fx.gen_result("2","Problem is used",list(cursor)))
                return

            result = db.problems.find_one({"name":problem})['archive']
            result = not result
            db.problems.update({"name":problem},{"$set":{"archive":result}})
            if result:
                self.write(fx.gen_result("0","Problem added to archive"))
            else:
                self.write(fx.gen_result("0","Problem removed from archive"))


    class ArchiveViewHandler(BaseHandler,tornado.web.RequestHandler):
        @tornado.web.authenticated
        def get(self):            
            if self.current_user['user_class'] == 0:
                submissions = db.submissions.find({"contest":None,"user.email":self.current_user["email"]}).sort("time",-1)
            else:
                submissions = db.submissions.find({"contest":None}).sort("time",-1)

            submissions = list(submissions)
            for i in xrange(len(submissions)):
                submissions[i]['score'] = str(models.Submission.get_submission_score(submission=submissions[i]["id"]))+"%"

            page_data = dict(
                title = "Submissions",
                user = self.current_user,
                submissions = list(submissions)
                ) 
            self.render("submissions.html",**page_data)


class Scoreboard():
    class ScoreoardHandler(BaseHandler,tornado.web.RequestHandler):
        def get(self):
            if (self.current_user["user_class"] != 1):
                self.set_status(403)
                self.finish("Forbidden")
                return
            data = []
            users = []
            trash = []
            contest = self.get_argument('contest','Colegii Mari')
            #"user.email":{"$nin":["test","dimasavva17@gmail.com"]}
            submissions = list(db.submissions.find({"contest":contest},{"_id":False,"id":True,"score":True,"user":True,"problem":True,"contest":True}).sort("time",pymongo.DESCENDING))
            for item in submissions:
                current = dict(
                    user = item["user"],
                    problem = item["problem"],
                    contest = item["contest"],
                    )
                if item["user"] not in users:
                    users.append(item["user"])

                if current in trash:
                    continue

                new = copy.copy(current)
                new["score"] = item["score"]
                trash.append(current) 
                data.append(new)
                #data[len(data)-1]["score"] = item["score"]
            
            #Parse
            score = []
            for user in users:
                curr = {"score":0,"problems":{},"user":user["name"]}
                for item in data:
                    if item["user"] != user:
                        continue
                    curr["score"] += int(item['score'])
                    curr["problems"][item["problem"]] =int(item["score"])
                score.append(curr)
            score = list(reversed(sorted(score,key=lambda k: k['score'])))
            #print(score)
            page_data = dict(
                title = 'Scoreboard',
                user = self.current_user,
                problems = db.contests.find_one({"name":contest})['problems'],
                score = score
                )
            self.render("scoreboard.html",**page_data)

    class ScoreboardExportHandler(BaseHandler,tornado.web.RequestHandler):
        def get(self):
            data = dict()
            users = []
            trash = []
            contest = self.get_argument('contest','seniori')
            submissions = list(db.submissions.find({"contest":contest,"user.email":{"$nin":["test","dimasavva17@gmail.com"]}},{"_id":False,"time":True,"id":True,"score":True,"user":True,"problem":True,"contest":True,"data":True}))
            
            for item in submissions:
                if item["user"]["email"] not in data.keys():
                    email = item["user"]["email"]
                    data[email]= dict()
                    data[email]["name"] = item["user"]["name"]
                    data[email]["score"] = 0
                    data[email]["problems"] = dict()


            for item in submissions:
                email = item["user"]["email"]
                if item["problem"] not in data[email]["problems"].keys():
                    data[email]["problems"][item["problem"]] = dict()

            for item in submissions:
                email = item["user"]["email"]
                problem = item["problem"]
                time = item["time"]
                submission_data = item["data"]
                score = item["score"]
                if not "time" in data[email]["problems"][problem].keys() or time>data[email]["problems"][problem]["time"]:
                    curr = dict(
                        time = time,
                        data = submission_data,
                        score = score
                        )
                    data[email]["problems"][problem] = curr

            for user in data.keys():
                print user
                for problem in data[user]["problems"]:
                    data[user]["score"] += int(data[user]["problems"][problem]["score"])

            #self.write(json.dumps(data)) 
            self.render("export.html",data=data)


class Submission():
    class SumbissionHandler(BaseHandler,tornado.web.RequestHandler):
        def put(self):
            submission = dict()
            try:
                data = json.loads(self.request.body)
            except:
                self.write(fx.gen_result("1","Wrong request"))
                return

            fields = ["email","contest","language","source","problem"]

            if not set(fields).issubset(data):
                self.write(fx.gen_result("2","Missing data"))
                return

            submission['user'] = {'email':data['email'], 'user_class':0, 'name':data['email']}
            n = db.users.find({"email":submission['user']['email']}).count()
            if n == 0:
                self.write(fx.gen_result("3","No user"))
                return

            filename = data['problem']

            submission['contest'] = data['contest']
            submission['problem'] = filename
            submission['lang'] = data['language']
            n = db.contests.find({"problems":submission['problem'],"name":submission['contest']}).count()
            if n == 0:
                self.write(fx.gen_result("5","No such problem"))
                return

            if not (submission['lang'] in ["pas","c","cpp"]):
                self.write(fx.gen_result("6","Wrong language"))
                return

            submission['time'] = now()
            submission['id'] = int(fx.get_submission_id())
            submission['body'] = data['source']
 

            submission_obj = models.Submission(**submission)
            result = submission_obj.validate()
            if not result:
                self.write(fx.gen_result("7","Security alert"))
                return
            result = submission_obj.add()
            print "\n"
            pprint(submission)
            f = open("data/users/"+submission["user"]['email']+"/"+str(int(submission["id"]))+"."+submission["lang"],"w")
            f.write(submission['body'])
            f.close()
            self.write(fx.gen_result(**result))

        @tornado.web.authenticated
        def post(self):
            curr_time = now()
            last = db.submissions.find_one({"user":self.current_user},sort=[("time", pymongo.DESCENDING)])
            if last and curr_time-int(last["time"]) < 20:
                self.write(fx.gen_result("6","Wait for 20 seconds"))
                return
            try:
                source = self.request.files['source']
                if len(source[0]['body']) > 1024*1024:
                    self.write(fx.gen_result("6","File too big"))
                    return
            except:
                self.write(fx.gen_result("2","No source"))
                return
            contest = self.get_argument("contest",None)

                
            filename = source[0]['filename'].split('.')
            problem = filename[0]
            if len(filename) < 2:
                lang = "exe"
            else:
                lang = filename[1]
            body = source[0]['body']
            print problem
            if not (lang in ["pas","c","cpp"]):
                self.write(fx.gen_result("4","Wrong language"))
                return

            if contest:
                n = db.contests.find({"problems":problem,"name":contest}).count()
            else:
                n = db.problems.find({"name":problem,"archive":True}).count()
            if n == 0:
                self.write(fx.gen_result("4","No such problem"))
                return

            time = now()
            if contest:
                n = db.contests.find({
                "start" : { "$lte": time },
                "end" : { "$gte" : time }
                }).count()

                if n == 0:
                    self.write(fx.gen_result("5","Too late"))
                    return

            submission_data = dict(
                user = self.current_user,
                problem = problem,
                time = time,
                contest = contest,
                lang = lang,
                id = fx.get_submission_id(),
                body = body
                )
            submission = models.Submission(**submission_data)
            result = submission.validate()
            if not result:
                self.write(fx.gen_result("1","Security alert"))
                return

            result = submission.add()
            os.umask(0)
            f = open("data/users/"+self.current_user["email"]+"/"+str(int(submission_data["id"]))+"."+submission_data["lang"],"w")
            f.write(body)
            f.close()
            self.write(fx.gen_result(**result))
            
        @tornado.web.authenticated
        def get(self):
            id = self.get_argument("id",None)
            if not id:
                submissions = db.submissions.find({"user.email":self.current_user['email']}).sort("time",-1)
                self.write(dumps(list(submissions)))
                return

            submission = db.submissions.find_one({"id":int(id)})

            if not submission:
                self.write(fx.gen_result("1","Error"))
                return

            field = "result"
            type = self.get_argument("type",None)
            if self.current_user['user_class'] == 1 and not type:
                field = "data"

            if self.request.headers.get('Referer').split("/")[-2] == "archive":
            	field = "data"

            if not submission[field]:
            	field = "result"
            self.write(fx.gen_result("0","Success",submission[field]))

    class SubmissionViewHandler(BaseHandler,tornado.web.RequestHandler):
        @tornado.web.authenticated
        def get(self):
            if self.current_user["user_class"] == 0:
                self.redirect("/home")
                return

            submissions = db.submissions.find({"contest":{"$ne":None}}).sort("time",-1).limit(100)
            page_data = dict(
                title = "Submissions",
                user = self.current_user,
                submissions = list(submissions)
                ) 
            self.render("submissions.html",**page_data)

    class SubmissionRejudgeHandler(BaseHandler,tornado.web.RequestHandler):
        @tornado.web.authenticated
        def post(self):
            if self.current_user['user_class'] == 0:
                self.redirect("/home")
                return

            type = self.get_argument("type",None)
            if not type:
                self.write(fx.gen_result("1","No type specified"))
                return


            if type == "submission":
                submission = self.get_argument("submission",None)
                if not submission:
                    self.write(fx.gen_result("2","No submission specified"))
                    return
                db.submissions.update({"id":int(submission)},{"$set":{"status":"pending"}})


class Contests():
    class ContestsHandler(BaseHandler,tornado.web.RequestHandler):
        @tornado.web.authenticated
        def get(self):
            user = self.current_user
            if user["user_class"] < 1:
                return
            user = models.User(**self.current_user)
            user_data = user.get_user_info()
            contests = list(db.contests.find())
            problems = list(db.problems.find())
            page_data = dict(
                title = "Contests",
                user = user_data,
                contests = contests,
                problems = problems
                )
            self.render("contests.html",**page_data)

        @tornado.web.authenticated
        def post(self):
            user = self.current_user
            if user["user_class"] < 1:
                return
            data = urllib.unquote(self.request.body).decode('utf8').split('&')
            name = self.get_argument('name',None)
            start_date = self.get_argument("start_date",None)
            start_time = self.get_argument("start_time",None)
            end_date = self.get_argument("end_date",None)
            end_time = self.get_argument("end_time",None)
            if not start_date or not start_time or not end_date or not end_time or not name:
                self.write(fx.gen_result("1","Missing data"))
                return

            #get problems
            problems = []
            for item in data:
                this = item.split('=')
                if this[0] == "problems":
                    problems.append(this[1])

            start = start_date+" "+start_time
            start = datetime.datetime.strptime(start,"%d-%m-%Y %H:%M:%S").strftime("%s")
            end = end_date+" "+end_time
            end = datetime.datetime.strptime(end,"%d-%m-%Y %H:%M:%S").strftime("%s")
            
            contest_data = dict(
                author = self.current_user,
                name = name,
                start = start,
                end = end,
                problems = problems,
                )
            contest = models.Contest(**contest_data)
            if contest.exists():
                self.write(fx.gen_result("1","Contests exists"))
                return

            result = contest.add()
            self.write(result)


class Problems():
    class ProblemsHandler(BaseHandler,tornado.web.RequestHandler):
        @tornado.web.authenticated
        def get(self):
            user = self.current_user
            if user["user_class"] < 1:
                return
            user = models.User(**self.current_user)
            user_data = user.get_user_info()
            problems = list(db.problems.find().sort("_id",-1))
            for i in xrange(len(problems)):
                problems[i]["submissions"] = models.Problem.count_submissions(name=problems[i]["name"])

            #pprint(problems)
            page_data = dict(
                title = "Problems",
                user = user_data,
                problems = list(problems)
                )
            self.render("problems.html",**page_data)

        @tornado.web.authenticated
        def post(self):
            user = self.current_user
            if user["user_class"] < 1:
                return

            required = ["name","memorylimit","timelimit","testcases"]
            problem_data = dict(
                name = self.get_argument('name',None),
                memorylimit = self.get_argument('memorylimit',None),
                timelimit = self.get_argument('timelimit',None),
                author = self.current_user
                )
            try:
                problem_data['testcases'] = self.request.files['testcases'][0]["body"]
            except:
                pass

            for field in required:
                if not problem_data[field]:
                    self.write(fx.gen_result("1","Missing data"))
                    return

            problem = models.Problem(**problem_data)
            if problem.exists():
                self.write(fx.gen_result("2","Problem exists"))
                return

            problem.set_dir()

            if problem_data['testcases']:
                result = problem.prepare_testcases()

                if result['status'] != "0":
                    self.write(fx.gen_result(**result))
                    return

            result = problem.add()
            self.write(result)


class Testcases(object):
    class TestcasesHandler(BaseHandler,tornado.web.RequestHandler):
        @tornado.web.authenticated
        def get(self):
            if self.current_user['user_class'] < 1:
                self.write(fx.gen_result("1","Non authorized"))
                return

            problem = self.get_argument("problem",None)
            if not problem:
                self.write(fx.gen_result("2","No problem"))
                return

            problem = db.problems.find_one({"name":problem})
            if not problem:
                self.write(fx.gen_result("3","DB Error"))
                return

            result = fx.gen_result("0","Ok",problem['testcases'])
            self.write(result)

    class TestcaseSetHandler(BaseHandler,tornado.web.RequestHandler):
        @tornado.web.authenticated
        def post(self):
            if self.current_user['user_class'] < 1:
                self.write(fx.gen_result("1","Non authorized"))
                return
            problem = self.get_argument("problem",None)
            testcase  = self.get_argument("testcase",None)
            testcase = int(testcase)-1
            value = 0
            value = self.get_argument("value",None)
            try:
                value = int(value)
            except:
                value = 0
            if not problem:
                self.write(fx.gen_result("1","Missing data"))
                return

            query = db.problems.update({'name':problem},{'$set':{'testcases.'+str(testcase): value}
                })

            self.write(fx.gen_result("0","Ok"))

    class TestcaseDownloadHandler(BaseHandler,tornado.web.RequestHandler):
        @tornado.web.authenticated
        def get(self):
            problem = self.get_argument("problem",None)
            if not problem:
                self.write(fx.gen_result("1","Problem not found"))
                return

            n = db.problems.find_one({"name":problem,"archive":True})
            if not n:
                self.write(fx.gen_result("2","Problem not archived"))
                return


            file_name = 'file.ext'
            buf_size = 4096
            self.set_header('Content-Type', 'application/zip')
            self.set_header('Content-Disposition', 'attachment; filename=' + problem+".zip")
            with open("data/problems/"+problem+"/testcases.zip", 'r') as f:
                while True:
                    data = f.read(buf_size)
                    if not data:
                        break
                    self.write(data)
            self.finish()


class Auth(object):
    class AuthHandler(BaseHandler,tornado.web.RequestHandler):
        def get(self):
            if self.current_user:
                self.redirect("/home")
            self.render("auth.html")

    class SignupHandler(tornado.web.RequestHandler):
        def post(self):
            #print self.request.body
            name = self.get_argument("name",None)
            email = self.get_argument("email",None)
            password = self.get_argument("password",None)
            if not name or not email or not password:
                self.finish(fx.gen_result("1","Missing data"))
                return
            user_data = dict(
                name = name,
                email = email,
                password = password
                )
            user = models.User(**user_data)
            result = user.signup()  
            print result
            self.write(result)

    class LoginHandler(tornado.web.RequestHandler):
        def post(self):
            email = self.get_argument("email",None)
            password = self.get_argument("password",None)
            if not email or not password:
                self.finish(fx.gen_result("1","Missing data"))
                return
            user_data = dict(
                email = email,
                password = password,
                )
            user = models.User(**user_data)
            result = json.loads(user.authenticate())
            if(result['status'] != '0'):
                self.write(json.dumps(result))
                return
            self.set_secure_cookie("user", tornado.escape.json_encode(result["data"]))
            self.write(json.dumps(result))

    class LogoutHandler(tornado.web.RequestHandler):
        def get(self):
            self.clear_cookie("user");
            self.redirect("/")

                

def start():

    os.umask(0) 
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

class MyDaemon(Daemon):
    def run(self):
        start()

if __name__ == "__main__":
    daemon = MyDaemon('/tmp/teamcode-frontend.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            print 'started'
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            start()
            #print "Unknown command"
            #sys.exit(2)
        sys.exit(0)
    else:
        start()
        #print "usage: %s start|stop|restart" % sys.argv[0]
        #sys.exit(2)
