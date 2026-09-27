import Alert from "@mui/material/Alert";
import { useState } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import Button from "@mui/material/Button";
import RadioGroup from "@mui/material/RadioGroup";
import Radio from "@mui/material/Radio";
import FormControlLabel from "@mui/material/FormControlLabel";

import { PageContainer } from "../../components/layout/PageContainer";
import { CollapsibleAside } from "../../components/layout/CollapsibleAside";
import { DonutProgress } from "../../components/progress/DonutProgress";
import { StreakBadge } from "../../components/badge/StreakBadge";
import { PhosphorIcon } from "../../components/icon/PhosphorIcon";
import { NUMERIC_FONT_FAMILY } from "../../theme";
import { useQuiz } from "./useQuiz";
import { CHOICE_LETTERS } from "./quizHandoff";

// !NOTE: 選択肢の状態色(未選択/選択中/正解/不正解)はtheme.palette.accentの
//        3段階(main/light/wash)に収まらない専用の中間シェードを含むため、
//        Tag/ShortcutCard等とは異なりテーマ参照ではなくこの関数内に直書きしている。
function choiceStyle(
  index: number,
  selectedIndex: number | null,
  correctIndex: number | undefined,
  answered: boolean,
) {
  if (!answered) {
    return index === selectedIndex
      ? {
          bg: "var(--color-blue-100)",
          border: "var(--color-blue-400)",
          color: "var(--color-blue-500)",
          lbg: "var(--color-blue-400)",
          lcolor: "var(--color-on-pastel)",
        }
      : {
          bg: "var(--color-panel)",
          border: "var(--color-border)",
          color: "var(--color-text)",
          lbg: "var(--color-bg)",
          lcolor: "var(--color-text-sub2)",
        };
  }
  if (index === correctIndex) {
    return {
      bg: "var(--color-green-100)",
      border: "var(--color-green-400)",
      color: "var(--color-green-500)",
      lbg: "var(--color-green-500)",
      lcolor: "var(--color-panel)",
    };
  }
  if (index === selectedIndex) {
    return {
      bg: "var(--color-pink-100)",
      border: "var(--color-pink-400)",
      color: "var(--color-pink-500)",
      lbg: "var(--color-pink-500)",
      lcolor: "var(--color-panel)",
    };
  }
  return {
    bg: "var(--color-panel)",
    border: "var(--color-border)",
    color: "var(--color-text)",
    lbg: "var(--color-bg)",
    lcolor: "var(--color-text-sub2)",
  };
}

export function QuizPage() {
  const { error, submitting, progress, question, categoryFilter, selectedIndex, result, selectCategory, selectChoice, submitAnswer, nextQuestion } =
    useQuiz();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  if (!progress || !question) {
    return (
      <PageContainer>
      {error && <Alert severity="error">{error}</Alert>}
        <div style={{ padding: 36 }}>読み込み中…</div>
      </PageContainer>
    );
  }

  const answered = result !== null;

  return (
    <PageContainer>
      {error && <Alert severity="error">{error}</Alert>}
      <div style={{ display: "flex", minHeight: 640 }}>
        <CollapsibleAside
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          width={236}
          title="進捗・分野"
          sx={{
            background: "var(--color-panel)",
            borderRight: "1px solid var(--color-border-soft)",
            padding: "24px 18px",
            display: "flex",
            flexDirection: "column",
            gap: 20,
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
            <DonutProgress
              percent={progress.certification.achievementPercent}
              size={104}
              color="var(--color-blue-400)"
              trackColor="var(--color-blue-100)"
              label={`${progress.certification.achievementPercent}%`}
              subLabel="達成"
            />
            <div style={{ textAlign: "center" }}>
              <div style={{ fontWeight: 800, fontSize: 15, color: "var(--color-text)" }}>{progress.certification.name}</div>
            </div>
          </div>
          <Box sx={{ display: "flex", flexDirection: "column", gap: "9px" }}>
            <Box sx={{ fontWeight: 700, fontSize: 12, color: "var(--color-text-sub)", padding: "0 2px" }}>分野</Box>
            <List sx={{ padding: 0, display: "flex", flexDirection: "column", gap: "0px" }}>
              {progress.categories.map((category) => {
                const active = categoryFilter === category.id || (categoryFilter === null && category.id === question.category);
                return (
                  <ListItemButton
                    key={category.id}
                    selected={active}
                    onClick={() => selectCategory(category.id)}
                    sx={{
                      display: "block",
                      padding: "11px 13px",
                      borderRadius: "13px",
                      "&.Mui-selected, &.Mui-selected:hover": { background: "var(--color-blue-100)" },
                    }}
                  >
                    <Box sx={{ display: "flex", justifyContent: "space-between", fontWeight: active ? 700 : 600, fontSize: 13, color: active ? "var(--color-blue-500)" : "var(--color-text-sub2)" }}>
                      <span>{category.label}</span>
                      <Box component="span" sx={{ fontFamily: NUMERIC_FONT_FAMILY }}>
                        {category.percent}%
                      </Box>
                    </Box>
                    <Box sx={{ height: "7px", borderRadius: "7px", background: active ? "var(--color-blue-200)" : "var(--color-bg-alt)", marginTop: "6px" }}>
                      <Box sx={{ width: `${category.percent}%`, height: "100%", borderRadius: "7px", background: active ? "var(--color-blue-400)" : "var(--color-text-sub)" }} />
                    </Box>
                  </ListItemButton>
                );
              })}
            </List>
          </Box>
          <div style={{ marginTop: "auto" }}>
            <StreakBadge days={progress.streakDays} />
          </div>
        </CollapsibleAside>
        <main style={{ flex: 1, minWidth: 0, padding: "var(--page-gutter)", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <IconButton
                onClick={() => setSidebarOpen(true)}
                aria-label="進捗・分野を開く"
                sx={{ display: { xs: "inline-flex", md: "none" } }}
              >
                <PhosphorIcon name="ph ph-list" size={20} color="var(--color-text)" />
              </IconButton>
              <Box
                component="span"
                sx={{ fontFamily: NUMERIC_FONT_FAMILY, fontWeight: 800, fontSize: 13, color: "var(--color-blue-500)", background: "var(--color-blue-100)", padding: "5px 12px", borderRadius: "11px" }}
              >
                問題
              </Box>
              <span style={{ fontWeight: 600, fontSize: 12, color: "var(--color-text-sub)", display: "flex", alignItems: "center", gap: 5 }}>
                <i className="ph ph-bookmark-simple" style={{ fontSize: 15 }} />
                {progress.categories.find((c) => c.id === question.category)?.label}
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 7, fontWeight: 700, fontSize: 14, color: "var(--color-text-sub2)" }}>
              <i className="ph ph-timer" style={{ fontSize: 18 }} />
              {question.timeLimitSec}秒
            </div>
          </div>
          <div
            style={{
              fontWeight: 700,
              fontSize: 19,
              lineHeight: 1.6,
              color: "var(--color-text)",
              marginBottom: question.source ? 6 : 20,
              whiteSpace: "pre-wrap",
            }}
          >
            {question.text}
          </div>
          {question.source ? (
            <div style={{ fontWeight: 600, fontSize: 12, color: "var(--color-text-sub)", marginBottom: 20 }}>{question.source}</div>
          ) : null}
          <RadioGroup
            aria-label={question.text}
            value={selectedIndex === null ? "" : String(selectedIndex)}
            onChange={(_event, newValue) => selectChoice(Number(newValue))}
            sx={{ display: "flex", flexDirection: "column", gap: "11px" }}
          >
            {question.choices.map((choice, index) => {
              const style = choiceStyle(index, selectedIndex, result?.correctIndex, answered);
              const showMark = answered && (index === result?.correctIndex || index === selectedIndex);
              const isCorrectMark = index === result?.correctIndex;
              return (
                <FormControlLabel
                  key={index}
                  value={String(index)}
                  disabled={answered || submitting}
                  // !NOTE: 見た目上のカードはFormControlLabelのlabel部分として描画し、
                  //        Radio自体は視覚的に隠している。ネイティブradio要素を使うことで、
                  //        矢印キーでの選択肢間移動がブラウザ標準の挙動として手に入る
                  //        (List+ListItemButtonではroving tabindexを自前実装する必要があった)。
                  control={
                    <Radio
                      sx={{
                        position: "absolute",
                        inset: 0,
                        width: "100%",
                        height: "100%",
                        borderRadius: 0,
                        padding: 0,
                        margin: 0,
                        opacity: 0,
                      }}
                    />
                  }
                  label={
                    <Box sx={{ display: "flex", alignItems: "center", gap: "14px", flex: 1 }}>
                      <Box
                        sx={{
                          width: 30,
                          height: 30,
                          flex: "none",
                          borderRadius: "9px",
                          background: style.lbg,
                          color: style.lcolor,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontWeight: 800,
                          fontSize: 14,
                          fontFamily: NUMERIC_FONT_FAMILY,
                        }}
                      >
                        {CHOICE_LETTERS[index]}
                      </Box>
                      <Box component="span" sx={{ flex: 1, fontWeight: 600, fontSize: 15, color: style.color }}>
                        {typeof choice === "string" ? choice : <span>{choice.text}<img src={choice.imageUrl} alt={choice.alt} style={{ display: "block", maxWidth: "100%", width: 260 }} /></span>}
                      </Box>
                      {showMark ? (
                        <PhosphorIcon
                          name={isCorrectMark ? "ph-fill ph-check-circle" : "ph-fill ph-x-circle"}
                          size={22}
                          color={isCorrectMark ? "var(--color-green-500)" : "var(--color-pink-500)"}
                        />
                      ) : null}
                    </Box>
                  }
                  sx={{
                    position: "relative",
                    margin: 0,
                    alignItems: "center",
                    gap: "14px",
                    padding: "15px 17px",
                    borderRadius: "15px",
                    cursor: answered ? "default" : "pointer",
                    background: style.bg,
                    border: `1.5px solid ${style.border}`,
                    "& .MuiFormControlLabel-label": { flex: 1, color: "inherit" },
                    "&.Mui-disabled": { cursor: "default", opacity: 1 },
                  }}
                />
              );
            })}
          </RadioGroup>
          {result ? (
            <div style={{ marginTop: 18, background: "var(--color-panel)", border: "1.5px solid var(--color-blue-100)", borderRadius: 16, padding: "18px 20px" }}>
              {result.correct ? (
                <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 800, fontSize: 16, color: "var(--color-green-500)", marginBottom: 8 }}>
                  <i className="ph-fill ph-check-circle" style={{ fontSize: 20 }} />
                  正解！
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 800, fontSize: 16, color: "var(--color-pink-500)", marginBottom: 8 }}>
                  <i className="ph-fill ph-x-circle" style={{ fontSize: 20 }} />
                  おしい！もう一度確認しよう
                </div>
              )}
              <div style={{ display: "flex", gap: 9, alignItems: "flex-start" }}>
                <i className="ph-fill ph-lightbulb" style={{ color: "var(--color-orange-500)", fontSize: 18, marginTop: 2 }} />
                <div style={{ fontWeight: 500, fontSize: 13.5, lineHeight: 1.7, color: "var(--color-text)" }}>
                  {result.explanation}
                </div>
              </div>
            </div>
          ) : null}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "space-between", alignItems: "center", marginTop: "auto", paddingTop: 22 }}>
            <Link
              to="/study/chat"
              state={{ quizQuestion: { text: question.text, choices: question.choices } }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "12px 18px",
                background: "var(--color-panel)",
                border: "1px solid var(--color-border)",
                borderRadius: 14,
                fontWeight: 700,
                fontSize: 13.5,
                color: "var(--color-purple-500)",
                textDecoration: "none",
              }}
            >
              <i className="ph-fill ph-chat-circle-dots" style={{ fontSize: 17 }} />
              わからない → AIに聞く
            </Link>
            {answered ? (
              <Button
                onClick={nextQuestion}
                disableRipple
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "13px 26px",
                  background: "var(--color-blue-400)",
                  borderRadius: "14px",
                  fontWeight: 800,
                  fontSize: 14,
                  textTransform: "none",
                  color: "var(--color-on-pastel)",
                  boxShadow: "none",
                  "&:hover": { background: "var(--color-blue-400)" },
                }}
              >
                次の問題
                <PhosphorIcon name="ph-bold ph-arrow-right" />
              </Button>
            ) : (
              <Button
                onClick={submitAnswer}
                disabled={selectedIndex === null || submitting}
                disableRipple
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "13px 28px",
                  borderRadius: "14px",
                  fontWeight: 800,
                  fontSize: 14,
                  textTransform: "none",
                  cursor: selectedIndex === null ? "default" : "pointer",
                  background: selectedIndex === null ? "var(--color-bg-alt)" : "var(--color-blue-400)",
                  color: selectedIndex === null ? "var(--color-text-sub)" : "var(--color-on-pastel)",
                  "&:hover": { background: selectedIndex === null ? "var(--color-bg-alt)" : "var(--color-blue-400)" },
                }}
              >
                <PhosphorIcon name="ph-bold ph-check" />
                解答する
              </Button>
            )}
          </div>
        </main>
      </div>
    </PageContainer>
  );
}
