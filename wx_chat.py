# coding=utf8

import openai
import sys
import time
import werobot                                                                                                                                                                               
import threading
import requests
import json
import datetime
import traceback


# 以下四项需要根据微信公众后台配置填写
appid=""
appsecret=""
openai.api_key=""
robot = werobot.WeRoBot(token='')

opend_id_url_read_dict = dict()
conversation_msg_dict={}

def get_access_token(appid,appsecret):
    """ 
    获取微信公众号的access_token值
    """
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}'.\
        format(appid, appsecret)
    print(url,flush=True)
    headers = { 
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.67 Safari/537.36'
    }   
    response = requests.get(url, headers=headers).json()
    access_token = response.get('access_token')
    print(access_token,response,flush=True)
    return access_token


def sendmsg(msg,access_token,open_id):
    """ 
    给所有粉丝发送文本消息
    """
    url = "https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={}".format(access_token)
    print(url,flush=True)
    body = { 
        "touser": open_id,
        "msgtype":"text",
        "text":
        {   
            "content": msg 
        }   
    }   
    data = bytes(json.dumps(body, ensure_ascii=False).encode('utf-8'))
    print(data)
    response = requests.post(url, data=data)
    # 这里可根据回执code进行判定是否发送成功(也可以根据code根据错误信息)
    result = response.json()
    print(result)


def stream_generate_response(messages):
    start_time=time.time()
    content=messages.content

    openai_messages=[
        {"role":"user","content":content}
    ]
    open_id=messages.FromUserName
    if open_id not in conversation_msg_dict:
        conversation_msg_dict[open_id]=list()
    conversation_msg_dict[open_id].append({"role":"user","content":content})
    openai_messages=conversation_msg_dict[open_id] 

    completion=None
    try:
        completion =  openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=openai_messages,
            #prompt=content,
            #max_tokens=193,
            temperature=0,
            stream=True
        )
    except:
        completion=None
        print("catch exception,err_msg:%s" % traceback.format_exc())


    access_token=get_access_token(appid,appsecret)
    if not completion:
        sendmsg("当前请求人数过多，请稍后重试~~",access_token,open_id)		
        return 

    total_text=""
    completion_text=""
    collected_events=[]
    for event in  completion:
        if "content" in event['choices'][0]['delta']:
            completion_text += event['choices'][0]['delta']["content"]
            cur_time=time.time()
            if "\n" in event['choices'][0]['delta']["content"] and cur_time-start_time>=3:
                completion_text=completion_text.strip("\n")
                if completion_text:
                    print("completion_text:{} time_cost:{}s".format(completion_text,cur_time-start_time))
                    total_text += completion_text
                    sendmsg(completion_text,access_token,open_id)
                    start_time=time.time()
                completion_text=""
        if completion_text and not event['choices'][0]['delta']:
            print("completion_text:{} time_cost:{}s".format(completion_text,time.time()-start_time))
            total_text += completion_text
            sendmsg(completion_text,access_token,open_id)
            start_time=time.time()
            completion_text=""
    if total_text:
        conversation_msg_dict[open_id].append({"role":"assistant","content":total_text})
        if len(conversation_msg_dict[open_id])>6:
            conversation_msg_dict[open_id]=conversation_msg_dict[open_id][-6:] 
@robot.handler
def hello (messages):
    try:
        print(messages.content+"\tFromUserName:"+messages.FromUserName+"\tCreateTime:"+str(messages.CreateTime)+"\tToUserName:"+str(messages.ToUserName)+"\tMsgId:"+str(messages.MsgId)+"\tmessage_id:"+str(messages.message_id)+"\tsource:"+str(messages.source)+"\ttarget:"+str(messages.target)+"\ttime:"+str(messages.time)+"\ttype:"+str(messages.type),flush=True)
        t = threading.Thread(target=stream_generate_response, args=(messages,))                                                                                              
        t.start()
    except:
        print(traceback.format_exc())

robot.config['HOST'] = '0.0.0.0'
robot.config['PORT'] = 80
robot.run()
