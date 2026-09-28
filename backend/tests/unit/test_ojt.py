def test_list_departments(client):
    response = client.get("/api/ojt/departments")

    assert response.status_code == 200
    body = response.json()
    assert len(body["departments"]) == 6
    assert {d["id"] for d in body["departments"]} == {
        "dev",
        "qa",
        "sales",
        "design",
        "mfg",
        "ga",
    }


def test_get_department_messages(client):
    response = client.get("/api/ojt/departments/dev/messages")

    assert response.status_code == 200
    body = response.json()
    assert body["deptId"] == "dev"
    assert len(body["messages"]) == 1
    assert body["messages"][0]["role"] == "bot"


def test_get_department_messages_not_found(client):
    response = client.get("/api/ojt/departments/unknown/messages")

    assert response.status_code == 404


def test_get_department_knowledge(client):
    response = client.get("/api/ojt/departments/dev/knowledge")

    assert response.status_code == 200
    body = response.json()
    assert body["deptId"] == "dev"
    assert len(body["items"]) >= 1


def test_get_department_knowledge_not_found(client):
    response = client.get("/api/ojt/departments/unknown/knowledge")

    assert response.status_code == 404


def test_post_chat(client):
    response = client.post("/api/ojt/chat", json={"deptId": "dev", "text": "規約はどこ？"})

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "bot"
    assert "開発課" in body["text"]
    assert body["references"][0]["label"] == "コーディング規約 2026"
    assert body["references"][0]["quote"]


def test_post_chat_department_not_found(client):
    response = client.post("/api/ojt/chat", json={"deptId": "unknown", "text": "hi"})

    assert response.status_code == 404
