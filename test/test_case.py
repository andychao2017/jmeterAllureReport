#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 20.5.21 2:48 下午
# @Site    :
# @File    : .py
# @Software: PyCharm
import pytest
import allure
from util.xml2report import xml_2_data
from pytest_assume.plugin import assume
import test


API_FAILED_COUNT = 0


def assert_api_fail(msg):
    test.test_case.API_FAILED_COUNT += 1
    assert False, msg


@allure.step('{assert_name}')
def log_asserts(assert_name, failure, error, result):
    pass


@allure.step('{api_name}')
def log_api_result(api_name, url, method, duration, code, failed, asserts):
    if failed and asserts is not None:
        for a in asserts:
            name = a['name'] if 'name' in a and a['name'] is not None else ''
            name = name if isinstance(name, str) else name.decode('utf-8')
            failure = a['failure'] if 'failure' in a and a['failure'] is not None else ''
            failure = failure if isinstance(failure, str) else failure.decode('utf-8')
            error = a['error'] if 'error' in a and a['error'] is not None else ''
            error = error if isinstance(error, str) else error.decode('utf-8')
            msg = a['failureMessage'] if 'failureMessage' in a and a['failureMessage'] is not None else ''
            msg = msg if isinstance(msg, str) else msg.decode('utf-8')
            log_asserts(name, failure, error, msg)
            assert_api_fail(f'{name}: {msg}')
    elif failed and asserts is None:
        # allure.attach(str(api), name='call_info', attachment_type=allure.attachment_type.JSON)
        msg = f'Status Code is not 2xx. Return: {code}'
        # assert False, msg
        assert_api_fail(msg)
    elif not failed and asserts is not None:
        for a in asserts:
            name = a['name'] if 'name' in a and a['name'] is not None else ''
            name = name if isinstance(name, str) else name.decode('utf-8')
            failure = a['failure'] if 'failure' in a and a['failure'] is not None else ''
            failure = failure if isinstance(failure, str) else failure.decode('utf-8')
            error = a['error'] if 'error' in a and a['error'] is not None else ''
            error = error if isinstance(error, str) else error.decode('utf-8')
            msg = a['failureMessage'] if 'failureMessage' in a and a['failureMessage'] is not None else ''
            msg = msg if isinstance(msg, str) else msg.decode('utf-8')
            log_asserts(name, failure, error, msg)
    else:
        assert True


class Test:
    @allure.title("{tc_name}")
    @allure.feature("DMS")
    @pytest.mark.parametrize("tc_name, tc_result, tc_duration, case_results", xml_2_data())
    def test_dms(self, tc_name, tc_result, tc_duration, case_results):
        for step in case_results:
            with assume, allure.step(step['name']):
                for api in step['api_results']:
                    with assume:
                        log_api_result(api['name'], api["request_url"], api['method'], api["duration"],
                                       api["status_code"], api['api_fail'], api['asserts'])
                if test.test_case.API_FAILED_COUNT > 0:
                    test.test_case.API_FAILED_COUNT = 0
                    assert False, 'At least 1 api assert failed.'

