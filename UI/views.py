from jinja2 import Template
from elector.elector import SummerElector
from time import sleep
import os,json,threading

from bin.settings import CACHE_SESSION_PATH

from database.load import *

from login.session import SummerSession

from database.mainDB import MainDB


SESSION_STATUS = {0: 'NOT_INIT', 1: 'INIT', 2: 'LOGIN_SUCCESS', 3: 'TEMPORARY_LOGIN_FAILED',
                  4: 'FAILED_AND_QUIT', 5: 'TIME_OUT', 6: 'UNKNOWN_ERROR'}

ELECTOR_STATUS = {0:'NOT_INIT',1:'INIT',2:'SUBMIT_SUCCEES',3:'SUBMIT_FAILED',4:'UNKNOWN_ERROR'}

# class TestThread(threading.Thread):
#     def __init__(self,mainStatus):
#         self.mainStatus=mainStatus
#         threading.Thread.__init__(self)
#     def run(self):
#         print("login:"+str(self.mainStatus.logInStatus))
#         print("elector:"+str(self.mainStatus.electorStatus))
#         sleep(5)


class MainStatus:
    def __init__(self):
        self.ifLogIn = False
        self.logInStatus = 0  # 0:not_init 1:init 2:success 3:failed 4:failed and quit 5:unknown error
        self.logInMessage = ""

        self.electorThread = 0
        self.electorStatus = 0
        self.electorMessage = ""

        self.username = ""
        self.password = ""
        self.session = 0

        self.messageToUI=""


class ThreadingElector(threading.Thread):
    def __init__(self,bsid,session,mainStatus,mainDBdict,mutex):
        self.bsid=bsid
        self.session=session
        self.mainStatus=mainStatus
        self.mutex=mutex
        threading.Thread.__init__(self)
        self.elector=SummerElector(session,mainStatus,mainDBdict,mutex)
    def run(self):
        self.elector.select_course_by_bsid(self.bsid)

mainStatus=MainStatus()
mainStatusMutex=threading.Lock()

db=MainDB()

db.load_data(loaddata())

# tthread=TestThread(mainStatus)
# tthread.start()




TEST_PAGE="""<!DOCTYPE html>
<html>
<head>
<link href="/css/test.css" rel="stylesheet" />
</head>
<body>
<div class="test">
<p>Test:红帽子</p>
<p>设置PyCharm支持中文</p>
</div>
<div>
<img src="/static/image/test.jpg" />
</body>
</html>
"""

DEFAULT_ERROR_MESSAGE = """\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
        "http://www.w3.org/TR/html4/strict.dtd">
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8">
        <title>Error response</title>
    </head>
    <body>
        <h1>Error response</h1>
        <p>Error code: %(code)d</p>
        <p>Message: %(message)s.</p>
        <p>Error code explanation: %(code)s - %(explain)s.</p>
    </body>
</html>
"""
# class TestMainDB:
#     def get_summer_course(self):
#         return{"dicts":[{"B":"BBB","C":"CCC","D":"DDD","E":"EEE"},
#                {"B":"BBB","C":"CCC","D":"DDD","E":"EEE"},
#                {"B": "BBB", "C": "CCC", "D": "DDD", "E": "EEE"}]}
#     def search(self,keyword):
#         return {"dicts":[{"B":keyword,"C":keyword,"D":keyword,"E":keyword}]}



class FileOpeningError:
    pass



class ViewsResponse:
    def __init__(self, content, head={}, status=200):
        self.status=status
        self.head=head
        self.content=content.encode("UTF-8")
        if status==200:
            self.head["Content-type"] = "text/html;charset=UTF-8"
        if len(self.content)!=0:
            self.head["Content-Length"]=str(len(self.content))


class ViewsAjaxResponse(ViewsResponse):
    def __init__(self,dict):
        ViewsResponse.__init__(self,json.dumps(dict),{})

class ViewsRedirect(ViewsResponse):
    def __init__(self,url="/"):
        ViewsResponse.__init__(self,"",head={"Location":url},status=301)











def open_file_as_string(filepath):

    filepath=os.path.dirname(__file__)+filepath

    if os.path.exists(filepath):
        try:
            f=open(filepath, "rb")
            result = (f.read()).decode('utf-8','ignore')
            f.close()
            return result
        except:
            raise FileOpeningError
    else:
        raise FileNotFoundError


def command_selector(command,method,data):

    if command=="/test":
        return test(method,data)

    elif command=="/ajaxinteract":
        return ajax_interact(method,data)

    elif command=="/control":
        return control(method,data)

    elif command=="/":
        return index(method,data)

    elif command=="/login":
        return login(method, data)

    elif command=="/search":
        return search(method, data)

    elif command=="/logout":
        return logout(method,data)


    else:
        return


#Views:

def index(method,data):
    if method=="GET":
        with mainStatusMutex:
            ifLogIn=mainStatus.ifLogIn
        if ifLogIn:
            indexT=Template(open_file_as_string('/static/template/index.html'))
            db_data=db.search("-all")
            result=indexT.render(db_data)
            return ViewsResponse(result)

        else:
            return ViewsRedirect("/login")
    else:
        return ViewsRedirect("/")

def login(method,data):
    with mainStatusMutex:
        ifLogIn=mainStatus.ifLogIn
    if ifLogIn:
        return ViewsRedirect("/")
    elif method=="GET":
        return ViewsResponse(open_file_as_string("/static/template/login.html"))
    elif method=="POST":
        if os.path.exists(CACHE_SESSION_PATH):
            os.remove(CACHE_SESSION_PATH)
        session=SummerSession(data['user'],data['pass'],mainStatus,mainStatusMutex)
        with mainStatusMutex:
            mainStatus.session=session
            mainStatus.username,mainStatus.password = data['user'],data['pass']
            mainStatus.ifLogIn = True
        return ViewsRedirect("/")
    else:
        return ViewsRedirect("/")

def logout(method,data):
    with mainStatusMutex:
        mainStatus.username, mainStatus.password="",""
        mainStatus.ifLogIn=False
    if os.path.exists(CACHE_SESSION_PATH):
        os.remove(CACHE_SESSION_PATH)
    return ViewsRedirect("/login")

def search(method,data):

    if method == "GET":
        return ViewsRedirect("/")

    else:
        if not data["keywords"]:
            return ViewsRedirect("/")
        else:
            db_result = db.search(data["keywords"])
            searchT = Template(open_file_as_string('/static/template/index.html'))
            result = searchT.render(db_result)
            return ViewsResponse(result)

def control(method,data):
    if method=="POST":
        command=data['ctlcmd']
        if data['value']:
            target=int(data['value'])
        if command=="electbybsid":
            thread=ThreadingElector(target,mainStatus.session,mainStatus,db.dbdict,mainStatusMutex)
            with mainStatusMutex:
                mainStatus.electorThread=thread
            thread.start()
        if command=="exit":
            os._exit(0)
        else:
            pass

    return ViewsResponse("",{},304)

def ajax_interact(method,data):
    responsedict={}
    with mainStatusMutex:
        responsedict['loginstatus']=mainStatus.logInStatus
        responsedict['loginmessage']=mainStatus.logInMessage
        responsedict['electorstatus']=mainStatus.electorStatus
        responsedict['electormessage']=mainStatus.electorMessage
        responsedict['messagetoui']=mainStatus.messageToUI
    return ViewsAjaxResponse(responsedict)

def test(method,data):

    if method=="POST":
        for i in data:
            print("key:"+i+"\n"+"value:"+data[i])
        return ViewsResponse(TEST_PAGE)
    elif method=="GET":
        if not data:
            return ViewsResponse(TEST_PAGE)
        else:
            c=""
            for i in data:
                c += i + ':' + data[i] + "\r\n"
            return ViewsResponse(c)
    else:
        return ViewsRedirect('/css/test.css')




