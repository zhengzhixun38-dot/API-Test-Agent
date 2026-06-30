import requests

BASE_URL = "http://mock:8001"

TOKEN = "mock-token-2024"


def test_case_1f8588b7():
    url = BASE_URL + "/api/user/info"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    response = requests.get(url, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data

def test_case_74f0545a():
    url = BASE_URL + "/api/user/info"
    headers = {
        "Authorization": 'Bearer mock-token-2025',
    }
    response = requests.get(url, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data

def test_case_5223c873():
    url = BASE_URL + "/api/user/info"
    response = requests.get(url)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_8130c861():
    url = BASE_URL + "/api/user/info"
    headers = {
        "Authorization": '',
    }
    response = requests.get(url, headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_84a690cf():
    url = BASE_URL + "/api/user/info"
    headers = {
        "Authorization": 'mock-token-2024',
    }
    response = requests.get(url, headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_b4d358a5():
    url = BASE_URL + "/api/user/info"
    headers = {
        "Authorization": 'Bearer  mock-token-2024',
    }
    response = requests.get(url, headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_ac6bfb0c():
    url = BASE_URL + "/api/user/info"
    headers = {
        "Authorization": 'Bearer invalid-token',
    }
    response = requests.get(url, headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_dc4f841e():
    url = BASE_URL + "/api/user/info"
    headers = {
        "Authorization": 'Bearer expired-token-2023',
    }
    response = requests.get(url, headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_f317dcd2():
    url = BASE_URL + "/api/user/info"
    headers = {
        "Authorization": 'Bearer xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    }
    response = requests.get(url, headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data
