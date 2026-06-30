import requests

BASE_URL = "http://mock:8001"

TOKEN = "mock-token-2024"


def test_case_1403289e():
    url = BASE_URL + "/api/product/list"
    response = requests.get(url)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data

def test_case_93db3972():
    url = BASE_URL + "/api/product/list"
    params = {
        "page": 2,
        "page_size": 20,
        "keyword": '手机',
    }
    response = requests.get(url, params=params)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data

def test_case_3a27bfd1():
    url = BASE_URL + "/api/product/list"
    params = {
        "page_size": 10,
    }
    response = requests.get(url, params=params)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data

def test_case_664b610b():
    url = BASE_URL + "/api/product/list"
    params = {
        "page": 'abc',
    }
    response = requests.get(url, params=params)

    assert response.status_code == 422
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_3120bfdc():
    url = BASE_URL + "/api/product/list"
    params = {
        "page_size": 'xyz',
    }
    response = requests.get(url, params=params)

    assert response.status_code == 422
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_2dd94a62():
    url = BASE_URL + "/api/product/list"
    params = {
        "keyword": 123,
    }
    response = requests.get(url, params=params)

    assert response.status_code == 422
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_790370d1():
    url = BASE_URL + "/api/product/list"
    params = {
        "page": 0,
    }
    response = requests.get(url, params=params)

    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_072f2575():
    url = BASE_URL + "/api/product/list"
    params = {
        "page": -1,
    }
    response = requests.get(url, params=params)

    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_f6710655():
    url = BASE_URL + "/api/product/list"
    params = {
        "page_size": 0,
    }
    response = requests.get(url, params=params)

    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_41cc5e45():
    url = BASE_URL + "/api/product/list"
    params = {
        "page_size": 101,
    }
    response = requests.get(url, params=params)

    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_65b7f9c5():
    url = BASE_URL + "/api/product/list"
    params = {
        "keyword": 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    }
    response = requests.get(url, params=params)

    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_581027f0():
    url = BASE_URL + "/api/product/list"
    headers = {
        "Authorization": 'Bearer invalid-token-2024',
    }
    response = requests.get(url, headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data
