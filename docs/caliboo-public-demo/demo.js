"use strict";
// Fixed, fictional data only. No API, network request, analytics, editable inputs or storage.
const sample = Object.freeze({
  "current": {
    "keep": "別の演習データ10件で、SQLのWITH句とLEFT JOINを使い未登録の受講記録を抽出した。空欄のある行で結果が合わず、入力値・抽出条件・集計条件を個別に確認し、NULL条件の違いが原因と切り分けた。IS NULLを用いて修正し、3パターンで再確認した。",
    "problem": "例外条件を説明するのに時間がかかった。",
    "try": "次回、結合とNULLの確認手順をチェックリストにまとめる予定。"
  },
  "reports": [
    {
      "date": "11/24",
      "label": "SQLで集計・JOIN後の件数を確認",
      "keep": "演習用SQLiteの受講記録20件をSQLのSELECTとGROUP BYで日別に集計した。JOIN後に件数が増えたため、入力件数、結合キー、結合後件数を順に確認し、重複する結合先の行が原因と切り分けた。集計前に結合先をキー単位に整理して修正し、手計算で件数が一致することを確認した。"
    },
    {
      "date": "11/25",
      "label": "SQLで未登録を抽出・NULL条件を確認"
    }
  ]
});
// 独立Codex解析セッションの実出力（素材は完全架空）を固定収録。
const candidates = Object.freeze([
  {
    "kind": "得意な能力",
    "color": "green",
    "label": "SQL活用力",
    "reason": "本人の日報では、受講記録20件を日別の件数にまとめ、別の10件では未登録の記録だけを取り出した。知りたいことに合わせて、データのまとめ方と抽出条件を変えている。",
    "scope": "少量の受講記録を使ったSQL演習2件に限る。クエリ本体や実行結果は提出されておらず、大規模データでの性能や分析結果の解釈は未確認。",
    "growth": "別の題材で『何を1件と数えるか』『どの行を残すか』を先に書き、SQLと結果表を並べて説明する。",
    "evidence": [
      [
        "11/24 · Keep",
        "演習用SQLiteの受講記録20件をSQLのSELECTとGROUP BYで日別に集計した。"
      ],
      [
        "11/25 · Keep",
        "別の演習データ10件で、SQLのWITH句とLEFT JOINを使い未登録の受講記録を抽出した。"
      ]
    ]
  },
  {
    "kind": "得意な能力",
    "color": "green",
    "label": "原因を切り分ける力",
    "reason": "結合後に件数が増えたときは入力・キー・結合後の件数を順に調べ、結合先の重複を特定したと報告している。別の日には空欄のある行に注目し、入力値と条件を別々に調べてNULLの扱いに原因を絞った。",
    "scope": "SQLの結果が想定と異なった2件の自己申告に基づく。実際の調査過程や、別分野でも同じ方法を使えるかは未確認。",
    "growth": "次の不一致では、原因の候補ごとに『これが原因なら何が起こるか』を一行で予測し、確認結果と照らす。",
    "evidence": [
      [
        "11/24 · Keep",
        "JOIN後に件数が増えたため、入力件数、結合キー、結合後件数を順に確認し、重複する結合先の行が原因と切り分けた。"
      ],
      [
        "11/25 · Keep",
        "空欄のある行で結果が合わず、入力値・抽出条件・集計条件を個別に確認し、NULL条件の違いが原因と切り分けた。"
      ]
    ]
  },
  {
    "kind": "仕事の進め方の傾向",
    "color": "purple",
    "label": "修正後は結果を確かめる",
    "reason": "1日目は結合先を整理したあと、手計算した件数と照合した。2日目はNULLの条件を直したあと、3パターンで再確認した。どちらの日報でも、修正しただけで作業を終えていない。",
    "scope": "異なる2日の日報で繰り返された行動。3パターンの内訳やテストの網羅性、演習外での習慣は未確認。",
    "growth": "次の演習では、修正前に期待する結果を小さな表に書き、修正後の値と並べて残す。",
    "evidence": [
      [
        "11/24 · Keep",
        "集計前に結合先をキー単位に整理して修正し、手計算で件数が一致することを確認した。"
      ],
      [
        "11/25 · Keep",
        "IS NULLを用いて修正し、3パターンで再確認した。"
      ]
    ]
  }
]);
const $=id=>document.getElementById(id);
const stages=[0,1,2,3].map(i=>$("stage-"+i));
const roleNames=["新入社員","講師","講師","新入社員"];
const frameTitles=["今日のふり返り","解析サンプル","強み候補のレビュー","あなたの強み"];
let stage=0;
let filled=false;
let selected=[];
const goTo=(n,focus=true)=>{
  stage=n;
  stages.forEach((el,i)=>el.hidden=i!==n);
  $("role").textContent=roleNames[n];
  $("frame-title").textContent=frameTitles[n];
  document.querySelectorAll("#steps [data-stage]").forEach((el,i)=>{
    el.classList.toggle("complete",i<n);
    el.querySelector(".number").textContent=i<n?"✓":String(i+1);
    if(i===n)el.setAttribute("aria-current","step");else el.removeAttribute("aria-current");
  });
  if(focus){
    const h=$("stage"+n+"title");
    h.focus({preventScroll:true});
    h.scrollIntoView({block:"nearest",behavior:"auto"});
  }
};
function element(tag,content,cls){
  const el=document.createElement(tag);
  if(content!==undefined)el.textContent=content;
  if(cls)el.className=cls;
  return el;
}
function showSampleSources(){
  const node=$("source-list");
  node.replaceChildren();
  for(const report of sample.reports){
    const item=element("div",undefined,"source-item");
    item.append(element("span",report.date,"source-day"),element("span","提出済み · "+report.label),element("span","架空","badge done"));
    node.append(item);
  }
}
function showCandidateTags(){
  $("candidate-count").textContent="サンプル候補："+candidates.length+"件 · 本人にはまだ表示されません。";
  $("candidate-tags").replaceChildren(...candidates.map(c=>element("span",c.label,"tag "+c.color)));
}
function renderCandidate(c,reviewMode,i){
  const article=element("article",undefined,"card "+(c.color==="purple"?"purple-card":""));
  article.append(element("div",c.kind,"tag kind "+c.color),element("h3",c.label,"strength-label"),element("p","どんな行動から見えた？","detail-heading"),element("p",c.reason),element("p","評価の範囲："+c.scope,"scope"));
  if(reviewMode){
    const details=element("details");details.open=true;
    details.append(element("summary","原文根拠（架空の日報）"));
    for(const [source,quote] of c.evidence){
      const block=element("blockquote");block.append(element("span",source),document.createTextNode("「"+quote+"」"));details.append(block);
    }
    article.append(details);
    const label=element("label",undefined,"checkrow");
    const input=element("input");input.type="checkbox";input.setAttribute("data-candidate",i);
    input.addEventListener("change",()=>{
      selected=Array.from(document.querySelectorAll("[data-candidate]:checked"),el=>Number(el.dataset.candidate));
      $("approve").disabled=selected.length===0;
    });
    label.append(input,document.createTextNode("この候補を承認する"));article.append(label);
  } else {
    article.append(element("p","次の取り組み："+c.growth,"scope"));
  }
  return article;
}
function review(){
  selected=[];
  const node=$("review-cards");node.replaceChildren();
  candidates.forEach((c,i)=>node.append(renderCandidate(c,true,i)));
  $("approve").disabled=true;
  goTo(2);
}
function approve(){
  if(!selected.length)return;
  const node=$("result-cards");node.replaceChildren();
  selected.forEach(i=>node.append(renderCandidate(candidates[i],false,i)));
  $("growth").textContent=selected.map(i=>candidates[i].growth).join(" ");
  goTo(3);
}
function reset(focus=true){
  filled=false;selected=[];
  for(const field of ["keep","problem","try"])$(field).value="";
  $("mood").textContent="未選択";$("mood-comment").textContent="";$("mood-comment").hidden=true;$("submit").disabled=true;
  $("fill").disabled=false;$("analyze").disabled=false;$("review").disabled=true;
  $("analysis-status").textContent="解析サンプルを待機中";
  $("analysis-description").textContent="原文に基づく候補の再生を開始しましょう。";
  $("candidate-preview").hidden=true;
  $("review-cards").replaceChildren();$("result-cards").replaceChildren();
  $("growth").textContent="";$("approve").disabled=true;
  goTo(0,focus);
}
$("fill").addEventListener("click",()=>{
  if(stage!==0)return;
  for(const field of ["keep","problem","try"])$(field).value=sample.current[field];
  $("mood").textContent="未選択（コメントあり）";$("mood-comment").textContent="きもちのコメント：原因を一つずつ確認できて安心した。";$("mood-comment").hidden=false;filled=true;$("submit").disabled=false;$("fill").disabled=true;
});
$("submit").addEventListener("click",()=>{if(filled&&stage===0)goTo(1)});
$("analyze").addEventListener("click",()=>{
  if(stage!==1)return;
  $("analyze").disabled=true;
  $("analysis-status").textContent="解析サンプル表示完了";
  $("analysis-description").textContent=sample.reports.length+"件の原文から得た候補を再現しました。講師の確認へ進めます。";
  showCandidateTags();
  $("candidate-preview").hidden=false;$("review").disabled=false;
});
$("review").addEventListener("click",()=>{if(stage===1&&!$("review").disabled)review()});
$("approve").addEventListener("click",()=>{if(stage===2)approve()});
$("restart").addEventListener("click",()=>reset());
$("finish-reset").addEventListener("click",()=>reset());
showSampleSources();
reset(false);
