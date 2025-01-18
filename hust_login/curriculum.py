# 查询课表
import requests
import json
from .login import CheckLoginStatu
import re
from datetime import datetime, timedelta


def weeks_from(start_date, date):
    if not isinstance(start_date, datetime):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    date = datetime.strptime(date, '%Y-%m-%d')
    delta = date - start_date
    return delta.days // 7 + 1


def get_dates_between(start_date_iso, end_date_iso):
    # written by AI, tested OK
    start_date = datetime.fromisoformat(start_date_iso)
    end_date = datetime.fromisoformat(end_date_iso)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    num_days = (end_date - start_date).days + 1
    dates_list = [start_date + timedelta(days=i) for i in range(num_days)]

    return [date.date().isoformat() for date in dates_list]


def GetOneDay(session: requests.Session, date: str, preflight: bool = True) -> dict:
    '''
    PARAMETERS:\n
    session -- should be already logged in\n
    date    -- the day you want, in form of YYYY-MM-DD\n
    \n
    RETURN:\n
    [{'No':'1', 'ClassName': 'XXX', 'TeacherName': 'XXX'}}, ...], {'Date':'2023-01-01','InWeek':'星期一'}\n
    OR [],{'Date':'2013-01-01'}
    '''
    if not (isinstance(session, requests.Session) and isinstance(date, str)):
        raise TypeError('HUSTPASS: CHECK YOUR session, day AND week INPUT TYPE')

    if not CheckLoginStatu(session):
        raise ConnectionRefusedError('HUSTPASS: YOU HAVENT LOGGED IN')

    if preflight: session.get("https://hubs.hust.edu.cn/cas/login")  # Preflight

    date_query = datetime.strptime(date, '%Y-%m-%d').date().isoformat()  # 保证日期格式标准，即补充用户可能忘记添加的0

    resp_api = session.get(f'https://hubs.hust.edu.cn/schedule/getStudentScheduleByDate?DATE={date_query}')
    content = json.loads(resp_api.text)
    class_list = []
    ret = {'date': date_query}
    for index, item in enumerate(content, 1):
        if item['JSMC'] == '—':
            continue
        class_list.append({'No': str(index), 'course': item['KCMC'], 'teacher': item['JGXM'],
                           'place': item['JSMC'], 'start': item['QSJC'], 'end': item['JSJC'], 'target': item['KTMC'], })
    ret['curriculum'] = class_list
    return ret


def QuerySchedules(session: requests.Session, _date_query: str | list[str] | int | tuple[str, str],
                   semester: str = None) -> list:
    '''
    PARAMETERS:\n
    session -- should be already logged in\n
    date    -- str  : the day you want, in form of YYYY-MM-DD\n
            -- list : a list, each item in the same form as above\n
            -- int  : the week after the semester started\n
            -- tuple: two str, including the start and the end\n
    semester-- str  : the semester you want e.g. 20221:the first semester of 2022~2023 school year\n
    \n
    RETURN:\n
    [{'Date':'YYYY-MM-DD','Curriculum':[{'No':'1', 'ClassName': 'XXX', 'TeacherName': 'XXX'}]}]
    '''
    session.get("https://mhub.hust.edu.cn/cas/login")
    session.get("https://hubs.hust.edu.cn/cas/login")

    print(semester)
    if semester is not None:
        if not isinstance(semester, str) and len(semester) == 5:
            #     session.post('http://hub.m.hust.edu.cn/kcb/todate/XqJsonCourse.action',data={'xqh':int(semester)})
            # else:
            raise TypeError('HUSTPASS: SEMESTER INPUT TYPE ERROR')

    resp: list[dict] = session.get('https://mhub.hust.edu.cn/CommonController/getXqList').json()
    if semester is None:
        semester = resp[0]
    else:
        for item in resp:
            if item['XQH'] == semester:
                semester = item
                break
        else:
            raise ValueError('HUSTPASS: SEMESTER NOT FOUND')
    start_date_semester = datetime.strptime(semester["QSRQ"], '%Y-%m-%d')  # 从html抓取学期开始日期

    query_list = []

    if isinstance(_date_query, int):
        _week = _date_query
        start_date = start_date_semester + timedelta(weeks=_week)
        for i in range(7):
            query_list.append(((start_date + timedelta(days=i)).date().isoformat(), _week))

    elif isinstance(_date_query, tuple):
        if len(_date_query) != 2:
            raise ValueError('HUSTPASS: ONLY ("YYYY-MM-DD","YYYY-MM-DD") LIKE TUPLE IS ACCEPTED')
        _start_date, _end_date = _date_query
        query_list.extend([(qdate, weeks_from(start_date_semester, qdate))
                           for qdate in get_dates_between(_start_date, _end_date)])

    elif isinstance(_date_query, list):
        for _item in _date_query:
            if not isinstance(_item, str):
                raise ValueError('HUSTPASS:ONLY "YYYY-MM-DD" ITEM IS ACCEPTED')
            else:
                item = datetime.strptime(_item, '%Y-%m-%d').date().isoformat()
                query_list.append((item, weeks_from(start_date_semester, item)))

    elif isinstance(_date_query, str):
        date_query = datetime.strptime(_date_query, '%Y-%m-%d').date().isoformat()
        query_list.append((date_query, weeks_from(start_date_semester, date_query)))

    else:
        raise TypeError('HUSTPASS: UNSUPPORT TYPE')

    ret = []
    for pack in query_list:
        date, week = pack
        ret.append(GetOneDay(session, date, preflight=False))
    return ret
