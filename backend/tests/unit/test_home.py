def test_get_home_summary(client):
    response = client.get("/api/home/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["name"] == "ユウキ"
    assert body["certification"]["achievementPercent"] == 68
    assert body["strengths"] == []
    assert len(body["shortcuts"]) == 3
    assert [s["to"] for s in body["shortcuts"]] == ["/assignments", "/study", "/ojt"]
    assert body["hero"]["message"] == "おかえり、ユウキさん！今日の振り返りをしよう"


def test_home_summary_is_isolated_per_user(other_member_client):
    response = other_member_client.get("/api/home/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["name"] == "ソラ"
    assert body["certification"]["achievementPercent"] == 20
    assert body["hero"]["message"] == "おかえり、ソラさん！今日の振り返りをしよう"


def test_home_summary_available_for_admin(admin_client):
    """不変条件: 全ユーザーがhome_profileを1行持つため、講師でも200が返る。"""
    response = admin_client.get("/api/home/summary")

    assert response.status_code == 200
    assert response.json()["user"]["name"] == "佐藤先生"
