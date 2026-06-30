import requests

BASE_URL = "http://mock:8001"

TOKEN = "mock-token-2024"


def test_case_57a9c463():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "product_id": 1,
        "count": 2,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data

def test_case_0a012310():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "product_id": 50,
        "count": 999,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert "data" in data

def test_case_2f7f6b8d():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "count": 2,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_767926be():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "product_id": 1,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_0ed3538e():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "product_id": 'abc',
        "count": 2,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_c088a738():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "product_id": 1,
        "count": 'abc',
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_case_f7e6317d():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "product_id": 0,
        "count": 2,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_819edb29():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "product_id": -1,
        "count": 2,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_a2ba6e86():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "product_id": 1,
        "count": 0,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_ec786df4():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "product_id": 1,
        "count": -1,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_e27afbcc():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "product_id": 1,
        "count": 1000,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 400
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_0814faa5():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer mock-token-2024',
    }
    payload = {
        "product_id": 101,
        "count": 2,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 404
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_2dfe1acc():
    url = BASE_URL + "/api/order/create"
    payload = {
        "product_id": 1,
        "count": 2,
    }
    response = requests.post(url, json=payload)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data

def test_case_9492e6ac():
    url = BASE_URL + "/api/order/create"
    headers = {
        "Authorization": 'Bearer invalid-token',
    }
    payload = {
        "product_id": 1,
        "count": 2,
    }
    response = requests.post(url, json=payload, headers=headers)

    assert response.status_code == 401
    data = response.json()
    assert "code" in data
    assert "message" in data
