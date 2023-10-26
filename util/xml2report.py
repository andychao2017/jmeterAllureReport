#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 19.5.21 2:37 下午
# @Site    :
# @File    : xml2report.py
# @Software: PyCharm
"""
t表示从请求开始到响应结束的时间：time
lt表示整个的空闲时间
ts表示访问的时刻: date
s表示返回的结果true表示成功，false表示失败:status
lb表示标题:title
rc表示返回的响应码:status_code
rm表示响应信息:status_message
tn表示线程的名字“1-138”表示第1个线程组的第138个线程。:thread
dt表示响应的文件类型
by表示请求和响应的字节数
sample: Transaction Controller运行结果，业务层面的Test Step
httpSample: Transaction Controller下的每个http request运行结果，AllureReport层面的Test Step，是业务层面的Sub Step
testResults中，tn相同的sample组成一条test case
"""
# import xmltodict
import pytest
import json
from datetime import datetime
from util.path_manage import Path
from util.file_manage import YamlManage
import re
from pyxml2dict import XML2Dict


def xml_2_data(filename: str = 'result.xml'):
    jmeter_result_file = Path().get_xml_path(YamlManage('config.yml').get_data('env'), filename)
    try:
        jmeter_result_data = XML2Dict().parse(jmeter_result_file)
        dict_results = jmeter_result_data['testResults']
        samples = dict_results['sample'] if isinstance(dict_results['sample'], list) else [dict_results['sample']]
        tc_names = set([sample['@tn'] for sample in samples])
        results = []
        for tc_name in tc_names:
            results.append(parse_test_cases(tc_name, samples))
        return results
    except Exception as e:
        print(e)
        return [
            ('time', 'date', 'true', 'story', 'title', 'status_code', 'status_message', 'thread', 'assertion_name',
             'assertion_result',
             'response_data', 'sampler_data', 'request_data', 'request_header', 'request_url')]


def parse_test_cases(tc_name, samples):
    """
    解析测试用例，包含：用例名称、运行结果、用时
    :return:
    """
    # sample in xml represents a transaction controller, it's a bundle of api, but a logic step for business
    controllers = (sample for sample in samples if sample['@tn'] == tc_name)
    case_duration = 0
    case_fail = False
    case_step_results = []
    # case_step_results contains step_name, step_fail, step_duration, api_call_results
    for con in controllers:
        if 'httpSample' in con:
            api_in_con = parse_api_results(con['httpSample'])
            step_fail = True if [api['api_fail'] for api in api_in_con].count(True) > 1 else False
            step_duration = sum([int(api['duration']) for api in api_in_con])
            step_result = {'name': con["@lb"], 'step_fail': step_fail, 'step_duration': step_duration,
                           'api_results': api_in_con}
            case_step_results.append(step_result)
        else:
            # todo: parse bean shell sample
            pass
    case_fail = True if [step['step_fail'] for step in case_step_results].count(True) > 1 else False
    case_duration = sum([int(step['step_duration']) for step in case_step_results])
    return tc_name, case_fail, case_duration, case_step_results


def parse_api_results(api_call_results):
    """
    parse jmeter steps
    every transaction controller is considered as a bundle of steps
    every http request is considered as a test step for allure report
    result for every step should contains：
        - name
        - duration
        - date time
        - request url
        - request header
        - request data (query string)
        - status code
        - status message
        - response data
        - assertion: a list of dict, every assertion contains name and failure [default: false]
        - api fail: True = Any assert fail if asserts exist. Status code should be 2xx if no assert exist.
    :return: rr_apis: request result for api calls in given transaction controller
    """
    rr_apis = []
    for api in api_call_results:
        api_name = api['@lb']
        url = api['java.net.URL'] if 'java.net.URL' in api else ''
        header = api['requestHeader']['#text'] if 'requestHeader' in api and '#text' in api['requestHeader'] else ''
        query_string = api['queryString']['#text'] if 'queryString' in api and '#text' in api['queryString'] else ''
        response = api['responseData']['#text'] if 'responseData' in api and '#text' in api['responseData'] else ''
        asserts = api['assertionResult'] if 'assertionResult' in api else None
        api_fail = False
        if asserts is not None:
            for a in asserts:
                api_fail = True if a['failure'].lower() != 'false' or a['error'].lower() != 'false' else api_fail
                if api_fail:
                    break
        else:
            api_fail = True if api['@rc'][:1] != '2' else api_fail

        acr = {'name': api_name,
               'duration': api['@t'],
               'date': api['@ts'],
               'request_url': url,
               'request_header': header,
               'request_data': query_string,
               'status_code': api['@rc'],
               'status_message': api['@rm'],
               'response_data': response,
               'asserts': asserts,
               'api_fail': api_fail}
        rr_apis.append(acr)
    return rr_apis


def get_assertion(assertion):
    assertion_name, assertion_result = None, None
    if isinstance(assertion, list):
        for value in assertion:
            if 'failureMessage' in value and value['failureMessage'] is not None:
                assertion_result = value['failureMessage']
                assertion_name = value['name']
                break
    elif isinstance(assertion, dict):
        if 'failureMessage' in assertion and assertion['failureMessage'] is not None:
            assertion_result = assertion['failureMessage']
            assertion_name = assertion['name']
    return assertion_name, assertion_result


def set_fail_tag(data):
    # [('name', '响应断言'), ('failure', 'false'), ('error', 'false')])
    config = YamlManage('fail_analysis_cfg.yml').get_data('config')

    story = '未标记'
    for c1 in config:
        matches = c1.get('match_regex')
        is_matched = False
        for match in matches:
            is_matched = is_matched and do_match(match)  # 不同key之间 且
        if is_matched:  # 如果匹配到 则退出循环 当前case标记成功，如果没有 继续下一个配置对比
            story = c1.get('fail_type_desc')
            break
    return story


def do_match(data, match):
    key = match.get('key')
    values = match.get('values')
    is_matched = False
    if len(values) <= 0:
        return True
    for v in values:
        if re.search(v, data.get(key), flags=0) != None:
            is_matched = True  # values中的匹配 或关系
            break
    return is_matched


if __name__ == '__main__':
    print(xml_2_data())
