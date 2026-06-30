import requests

BASE_URL = "http://mock:8001"


def test_case_dd95bf2d():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'admin',
        "password": '123456',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data
    assert "token" in data.get("data", {}), f"data.token not found"
    assert "username" in data.get("data", {}), f"data.username not found"

def test_case_5802ba38():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'test_user',
        "password": 'pass123456',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data
    assert "token" in data.get("data", {}), f"data.token not found"
    assert "username" in data.get("data", {}), f"data.username not found"

def test_case_c165751d():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": '',
        "password": '123456',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_05bf0362():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'admin',
        "password": '',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_30fb1cab():
    url = BASE_URL + "/api/user/login"
    payload = {
        "password": '123456',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_be0c76ab():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'admin',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_51969f5b():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'admin<script>',
        "password": '123456',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_16af19d2():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'ad min',
        "password": '123456',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_9967b727():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'admin',
        "password": '123@#$',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_39c05580():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'ab',
        "password": '123456',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_8d971f91():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'abcdefghij1234567890',
        "password": '123456',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data
    assert "token" in data.get("data", {}), f"data.token not found"
    assert "username" in data.get("data", {}), f"data.username not found"

def test_case_ee9d4ac0():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'abcdefghij12345678901',
        "password": '123456',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_1e1a3801():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'admin',
        "password": '12345',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_f664e1b4():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'admin',
        "password": '123456',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data
    assert "token" in data.get("data", {}), f"data.token not found"
    assert "username" in data.get("data", {}), f"data.username not found"

def test_case_d4698ceb():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'admin',
        "password": '12345678901234567890',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data
    assert "token" in data.get("data", {}), f"data.token not found"
    assert "username" in data.get("data", {}), f"data.username not found"

def test_case_55ac97b7():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'admin',
        "password": '123456789012345678901',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_5a5368cf():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'admin',
        "password": 'wrongpass',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_5cf28ee6():
    url = BASE_URL + "/api/user/login"
    payload = {
        "username": 'nonexist',
        "password": '123456',
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data
