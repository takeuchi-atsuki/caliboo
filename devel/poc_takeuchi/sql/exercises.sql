-- name: inner_join
-- 提出行がある組だけを返す。未提出の利用者は消える。
SELECT a.id AS assignment_id, u.id AS user_id, s.id AS submission_id
FROM assignments AS a
CROSS JOIN users AS u
JOIN submissions AS s ON s.assignment_id = a.id AND s.user_id = u.id
ORDER BY a.id, u.id;

-- name: left_join
-- 提出行の有無を残すため、全課題×全利用者を起点にする。
SELECT a.id AS assignment_id, u.id AS user_id, s.id AS submission_id
FROM assignments AS a
CROSS JOIN users AS u
LEFT JOIN submissions AS s ON s.assignment_id = a.id AND s.user_id = u.id
ORDER BY a.id, u.id;

-- name: group_by
-- COUNT(score) は NULL の点数を数えない。
SELECT a.id AS assignment_id, COUNT(s.id) AS submissions,
       COUNT(s.score) AS scored, AVG(s.score) AS average_score
FROM assignments AS a
LEFT JOIN submissions AS s ON s.assignment_id = a.id
GROUP BY a.id
ORDER BY a.id;

-- name: missing_submissions
-- score IS NULL では「提出済み・未採点」も含めてしまう。
SELECT a.id AS assignment_id, u.id AS user_id
FROM assignments AS a
CROSS JOIN users AS u
LEFT JOIN submissions AS s ON s.assignment_id = a.id AND s.user_id = u.id
WHERE s.id IS NULL
ORDER BY a.id, u.id;

-- name: null_and_count
-- COUNT(*) は LEFT JOIN が作る行も数える。
SELECT u.id AS user_id, COUNT(*) AS joined_rows,
       COUNT(r.id) AS reports, COUNT(s.id) AS submissions,
       COUNT(s.score) AS scored
FROM users AS u
LEFT JOIN reports AS r ON r.user_id = u.id
LEFT JOIN submissions AS s ON s.user_id = u.id AND s.assignment_id = 10
GROUP BY u.id
ORDER BY u.id;

-- name: null_state
-- 提出行がない状態と、提出行の点数が NULL の状態を区別する。
SELECT u.id AS user_id,
       CASE WHEN s.id IS NULL THEN '未提出'
            WHEN s.score IS NULL THEN '提出済み・未採点'
            ELSE '採点済み' END AS state
FROM users AS u
LEFT JOIN submissions AS s ON s.user_id = u.id AND s.assignment_id = 10
ORDER BY u.id;
