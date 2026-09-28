from caliboo_api.data.home_data import fetch_home_summary


def test_fetch_home_summary(bootstrapped_db, user_ids):
    summary = fetch_home_summary(user_ids["yuki"])

    assert summary.user.name == "ユウキ"
    assert summary.user.streakDays == 12
    assert summary.certification.achievementPercent == 68
    assert summary.hero.message == "おかえり、ユウキさん！今日の振り返りをしよう"
    assert summary.strengths == []
    assert len(summary.shortcuts) == 3
    assert [s.to for s in summary.shortcuts] == ["/assignments", "/study", "/ojt"]


def test_fetch_home_summary_is_isolated_per_user(bootstrapped_db, user_ids):
    summary = fetch_home_summary(user_ids["sora"])

    assert summary.user.name == "ソラ"
    assert summary.user.streakDays == 3
    assert summary.certification.achievementPercent == 20
    assert summary.hero.message == "おかえり、ソラさん！今日の振り返りをしよう"
