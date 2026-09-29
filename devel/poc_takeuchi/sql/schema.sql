PRAGMA foreign_keys = ON;

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    body TEXT NOT NULL
);

CREATE TABLE assignments (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL
);

CREATE TABLE submissions (
    id INTEGER PRIMARY KEY,
    assignment_id INTEGER NOT NULL REFERENCES assignments(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    score INTEGER CHECK (score BETWEEN 0 AND 100),
    UNIQUE (assignment_id, user_id)
);

INSERT INTO users VALUES
    (1, '青木'), (2, '井上'), (3, '上田'), (4, '遠藤');
INSERT INTO reports VALUES
    (101, 1, '初日'), (102, 1, '二日目'), (103, 2, '初日');
INSERT INTO assignments VALUES
    (10, 'SQL'), (11, '3D');
INSERT INTO submissions VALUES
    (201, 10, 1, 90), (202, 10, 2, NULL),
    (203, 11, 1, 80), (204, 11, 3, 70);
