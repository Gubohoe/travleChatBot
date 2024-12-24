from flask import Flask, request, jsonify
import subprocess  # Streamlit 실행을 위해 추가
import pathlib, os, datetime, re
import textwrap
import google.generativeai as genai
import json, sys

app = Flask(__name__)

now = datetime.datetime.now()

GOOGLE_API_KEY ='AIzaSyBogQtrVL5P6qBu2NGZYD13QusSV7ERNvo'
genai.configure(api_key=GOOGLE_API_KEY)

his = []
Con = None
content = None
flag = False
summ_dic = {}

persona = """당신은 여행 플래너 입니다. 대화 내용을 토대로 여행 일정 및 계획, 활동을 요약해서 얘기해주시고 만약 숙소, 예산, 여행 테마, 교통 이야기가 있을 경우도 요약해서 함께 얘기 해주시고 없을 경우에는 항목은 출력하되 내용은 비워주세요,
                출력 형태
                {
                    20XX년 XX월 XX일 ~ XX일 XX 여행 계획
                    
                    여행테마: 내용
                    
                    여행기간: X박 X일(X월 X일 ~ X월 X일까지)
                    
                    예산: 언급 없을 경우 비워주세요
                    
                    목적지: X, X, X, X
                    
                    교통: 언급 없을 경우 비워주세요
                    
                    숙소: 언급 없을 경우 비워주세요
                    
                    일정:
                    X월/X일(X): 내용
                    
                    고려사항:
                    * 내용
                    
                    출력형태는 이걸로 고정(추가로 첨가하거나 삭제하지마세요)해서 출력해주시고 또 **~** 이런거 붙이지 말아주세요
                }"""

persona2 = f"""당신은 여행 기획에 도움을 주는 역할을 수행하는 여행 기획자 입니다.
1)오늘 기준 날짜는 {now}입니다. 
2)사용자가 하는 말을 토대로 여행계획을 구상할 수 있도록 도움이 되는 대화를 계속 이어주세요
3)사람과 이야기 하듯이 대화만으로 이어주세요(요약같은거 안해줘도 되요)
4)대화를 이어줄 때 한 대화에 여러가지를 내용을 넣지말고 하나만 넣어주세요(ex "늦은 시간까지 영업하는 곳을 찾아야 할 수도 있으니,  원하는 지역과 음식 종류 를 알려주시면 더욱 구체적인 정보를 드릴 수 있습니다. 그리고,  첫날 디즈니랜드에서 얼마나 늦게까지 머무를 예정인지 알려주시면,  교통편과 식사 시간 등을 고려하여 효율적인 일정을 짤 수 있습니다." 이러지 말고 "늦은 시간까지 영업하는 곳을 찾아야 할 수도 있으니,  원하는 지역과 음식 종류 를 알려주시면 더욱 구체적인 정보를 드릴 수 있습니다." 이렇게 내용 하나만 담아서 대화가 편하게 되도록)
5)대화를 이어줄 때 내용없는 의문형보다는 제안형으로 해주세요(ex "추가 요청 사항이 있으신가요?" 이런식이면 계획하기 힘드니가 "아직 예산을 정하지 않았는데 예산을 정해주세요")
6)자세한 정보는 제공이 안되니까 숙소나 항공권 예약해준다는 말은 하지 말아주세요(ex " 지역의 전통적인 분위기의 호텔이나 부티크 호텔들을 찾아보겠습니다", "몇 가지 후보를 찾았습니다! 가우디 건축물과 가까운 곳, 조금 더 조용한 골목길에 위치한 곳 등 다양한 옵션이 있어요. 사진과 함께 자세한 정보를 보여드릴까요?" 이러지 말고 숙소관련해서는 여행지에 따라서 "~근처 숙소를 예약하시는걸 추천드립니다" 이정도 수준으로만 해주세요)
"""

#STEP2
model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=persona)
model2 = genai.GenerativeModel("gemini-1.5-flash", system_instruction=persona2)

def Community(prompt):
    global Con, his  # 전역 변수 사용

    if Con is None:  # 첫 대화 시작
        Con = model2.start_chat(history=[])

    response = Con.send_message(prompt)
    his.append(prompt)
    his.append(response.text)

    return response.text
    
def extract_info(text):
    #여행 테마 추출
    theme = re.search(r"여행테마:\s*(.*)", text).group(1)
    
    #여행 기간 추출
    period = re.search(r"여행기간:\s*(.*)", text).group(1)
    
    #예산 추출
    budget = re.search(r"예산:\s*(.*)", text).group(1)
    
    #목적지 추출
    destinations = re.search(r"목적지:\s*(.*)", text).group(1).split(", ")
    
    #교통 수단 추출
    transport = re.search(r"교통:\s*(.*)", text).group(1)
    
    #숙소 추출
    accommodation = re.search(r"숙소:\s*(.*)", text).group(1)
    
    #일정 추출
    schedule = {}
    days = re.findall(r"(\d{1,2}월[/\s]\d{1,2}일\([^\)]+\)): (.*)", text) 
    for day, activity in days:
        schedule[day] = activity.strip()
        
    #고려사항 추출
    Considerations = {}
    cons = re.findall(r"\* (.+?)(?=\n|\Z)", text)
    for idx, cons in enumerate(cons, 1):
        Considerations[f"{idx}."] = cons.strip()

    dic = {
        "여행 테마": theme,
        "여행 기간": period,
        "예산": budget,
        "목적지": destinations,
        "교통": transport,
        "숙소": accommodation,
        "일정": schedule,
        "고려사항": Considerations
    }
    return dic

#STEP4
def summary(prompt_his):
    Conv = model.start_chat(history=[
    {
        "role" : "user",
        "parts" : [f"오늘 기준 날짜는 {now.year}입니다."]
    },
    {
        "role" : "model",
        "parts" : ["네 잘 알겠습니다. 여행 기간을 나타낼 때 참고하겠습니다."]
    },
    {
        "role" : "user",
        "parts" : [
            """
            발리는 어때? 발리는 해변도 아름답고, 자연도 멋지며, 다양한 문화적 경험을 할 수 있는 곳이라 여유롭게 즐길 수 있을 것 같아. 해변에서 수영하거나 리조트에서 쉬기도 좋고, 발리의 작은 마을들을 돌아보면서 현지 문화를 경험하는 것도 재미있을 거야.
            발리, 좋지! 그런데 발리에서 어떤 활동들을 할 수 있을지 궁금한데, 그냥 해변에서 놀고 리조트에서 쉬는 것만으로는 아쉬울 것 같아. 좀 더 특별한 경험을 할 수 있는 곳들이 있을까?
            그럼, 발리에서 유명한 관광지들 외에도, 현지적인 느낌을 받을 수 있는 마을이나 도시들을 돌아보는 건 어떨까? 발리에는 바다뿐만 아니라, 그곳의 독특한 문화와 역사도 느낄 수 있는 곳들이 많잖아. 예를 들어, 우붓(Ubud) 같은 작은 마을은 발리 전통 문화와 예술을 느낄 수 있는 좋은 곳이야. 전통 시장도 있고, 예술적인 분위기 가득한 거리도 있어.
            우붓이 그렇게 매력적인 곳이라니! 그럼 우붓에서 어떤 활동을 할 수 있을까? 발리의 전통적인 건축물이나 문화유산들을 구경하면서, 현지 미술품이나 공예품을 볼 수 있을 것 같아. 또한, 우붓의 유명한 **원숭이 숲(Monkey Forest)**도 볼 만한 명소지. 숲 속을 걸으며 원숭이들을 구경하고, 자연과 함께 여유를 즐길 수 있을 거야.
            우붓이 정말 흥미로운 곳이네! 그럼 첫날에는 리조트에서 쉬고, 둘째 날에는 우붓을 방문해서 역사적인 장소와 문화적인 명소를 구경하고, 그 후에는 **세미냑(Seminyak)**에서 쇼핑이나 카페에서 쉬면서 분위기를 즐기는 것도 좋을 것 같아. 세미냑은 발리에서 유명한 해변이기도 하고, 쇼핑과 레스토랑들이 많아서 하루를 보내기에 완벽한 곳이지.
            그렇게 하면 일정이 정말 좋을 것 같아! 첫날은 리조트에서 여유롭게 쉬고, 둘째 날에는 우붓에서 문화와 자연을 즐기고, 셋째 날에는 세미냑에서 쇼핑도 하고 바다도 즐기고. 그다음엔 발리의 탄중 벤웨(Tanjung Benoa) 해변으로 가서 물놀이도 하고, **누사 두아(Nusa Dua)**에서 여유롭게 시간을 보내는 것도 좋은 마무리가 될 거야.
            그럼, 1월 2일부터 5일까지 이 일정으로 가는 거 어때? 첫날은 리조트에서 편하게 쉬고, 둘째 날은 우붓에서 전통적인 문화와 자연을 즐기고, 셋째 날은 세미냑에서 쇼핑과 바다를 즐기고, 마지막 날은 탄중 벤웨와 누사 두아에서 해변을 즐기자!
            그거 정말 좋네! 숙소는 우붓 근처에 있는 리조트를 예약하면 좋겠어. 이렇게 하면 우붓으로 쉽게 이동할 수 있고, 리조트에서 여유도 즐기면서 다양한 활동을 할 수 있을 거야. 세미냑이나 다른 해변가도 가까워서 이동하기 편리하고.
            교통은 어떻게 할까? 발리에서 여러 곳을 돌아보려면 렌터카를 빌리는 게 좋을 것 같아. 발리는 크기도 적당하고, 도로도 잘 되어 있어서 렌터카로 다니면 편할 거야. 대중교통은 약간 불편할 수 있으니까 렌터카를 예약하는 게 나을 것 같아.
            그럼! 숙소와 렌터카만 예약하면 나머지 일정은 다 준비된 것 같아. 1월 2일부터 5일까지, 첫날 리조트에서 쉬고, 둘째 날에는 우붓을 방문하고, 셋째 날에는 세미냑을 즐기고, 마지막 날에는 해변에서 시간을 보내는 거야. 이렇게 계획을 세우면 발리의 매력을 만끽할 수 있을 거야!
            완전 좋아! 그럼 숙소와 렌터카 예약을 빨리 해야겠네. 발리에서 정말 멋진 여행이 될 것 같아!
            """
            ]
    },
    {
        "role" : "model",
        "parts" : [
            """
            2024년 1월 2일 ~ 5일 발리 여행 계획

            여행테마: 발리 문화 체험 & 휴양

            여행기간: 4박 5일 (1월 2일 ~ 5일)

            예산: 

            목적지: 우붓, 세미냑, 탄중 베노아, 누사 두아

            교통: 렌터카 예정

            숙소: 우붓 근처 리조트 예정

            일정:

            1월/2일(수):  도착 후 우붓 근처 리조트 체크인, 휴식
            1월/3일(목): 우붓 관광 (원숭이 숲 등), 전통 시장 방문, 문화유산 탐방
            1월/4일(금): 세미냑 이동, 쇼핑, 해변 휴식, 레스토랑 이용
            1월/5일(토): 탄중 베노아, 누사 두아 해변 방문, 물놀이, 휴식 후 출발

            고려사항:

            * 우붓 근처 리조트 예약 필요. 
            * 우붓과 세미냑, 해변 지역으로의 이동 편의성 고려.
            * 렌터카 예약 필요. 
            * 발리 도로 사정 및 운전 숙련도 고려.
            * 원숭이 숲 외에 구체적인 관광지는 언급되지 않았으나,  여행자의 선호도에 따라 우붓의 사원, 궁전, 
            * 벼랑 절벽 등을 추가적으로 방문 가능.
            * 쇼핑과 해변 휴식이 주요 목표.  
            * 세미냑의 특색있는 레스토랑과 카페 이용을 고려.
            * 해양 액티비티(스노클링, 다이빙 등) 참여 가능성 고려."""
            ]
    },
    ])

    Conv.send_message(prompt_his)
    #res = Conv.last.text
    res = extract_info(Conv.last.text)
       
    with open('result.json', 'w', encoding='utf-8') as json_file:
        json.dump(res, json_file, ensure_ascii=False, indent=4)
        
    return res

    
@app.route('/keyboard')
def Keyboard():
    dataSend = {
    "Subject":"OSSP",
    "user":"corona_chatbot"
    }
    return jsonify(dataSend)

@app.route('/message', methods=['POST'])
def Message():
    global Con, his, flag

    req = request.get_json()
    content = req['userRequest']['utterance']

    if content == "플래너 초기화":
        Con = None
        his = []
        flag = False # 
        dataSend = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "플래너가 초기화되었습니다."
                        }
                    }
                ]
            }
        }

    elif content == "플래너시작":
        if not flag: 
            flag = True 
            dataSend = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "안녕하세요!! 저와 함께 여행 계획을 세워봐요!!"
                        }
                    }
                ]
            }
        }
        else:
            res = Community(content) 
            dataSend = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"{res}"
                        }
                    }
                ]
            }
        }
            
    elif content == "종료":
        if flag:  # 플래너가 시작된 상태에서만 종료 처리
            summ_dic = summary(his)
            Con = None  # Chatsession 종료
            his = []      # 대화 기록 초기화
            flag = False # 플래너 시작 상태 초기화
            dataSend = {
                "version": "2.0",
                "template": {
                    "outputs": [
                          {
                            "basicCard": {
                              "title": "일정",
                              "description": "클릭하면 다음 페이지로 이동합니다.",
                              "buttons": [
                                {
                                  "action": "webLink",
                                  "label": "이동하기",
                                  "webLinkUrl": "13.209.166.175:51612"
                                }
                              ]
                            }
                          }
                        ]
                }
            }

    elif not flag: 
            dataSend = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "`플래너시작`을 입력해주세요!"
                        }
                    }
                ]
            }
        }

    else:  
        res = Community(content)
        dataSend = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"{res}" #수정필요
                        }
                    }
                ]
            }
        }

    return jsonify(dataSend)

if __name__ == "__main__":
    # Flask 서버 실행 전에 Streamlit 서버를 subprocess로 실행
    subprocess.Popen(["streamlit", "run", "ui2.py"])  # Streamlit 실행
    app.run(host='0.0.0.0', port = 5000)
