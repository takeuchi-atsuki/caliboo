"use strict";
// Fixed, fictional data only. No API, network request, analytics, editable inputs or storage.
const sample = Object.freeze({
  current: {
    keep: "前日の集計手順をチェックリスト化し、別の演習データ10件に適用。境界値と空欄の結果を手計算と照合し、誤りがないことを確認した。",
    problem: "例外条件の説明に時間がかかった。",
    try: "次回、チェックリストとサンプルを受講者に共有する予定。"
  },
  previous: "演習用の受講記録20件を集計し、手計算と照合したところ未入力1件を発見。抽出条件を修正し、3パターンで再確認した。"
});
// 独立Codex解析セッションの実出力（素材は完全架空）を固定収録。
const candidates = Object.freeze([
  {
    "kind": "得意な能力",
    "color": "green",
    "label": "集計結果から未入力を見つけ、抽出条件を見直す",
    "reason": "受講記録20件の集計を手計算と突き合わせ、未入力1件を発見して抽出条件を修正した。集計結果をうのみにせず、抽出条件の見直しにつなげた点に根拠がある。",
    "scope": "1日分の演習についての本人申告。抽出式や元データはなく、修正の正しさや大規模データへの適用は未検証。",
    "growth": "未入力を含む少数のサンプルで、条件の修正前後にどの行が抽出されるかを表に残す。",
    "evidence": [
      [
        "11/24 · Keep",
        "演習用の受講記録20件を集計し、手計算と照合したところ未入力1件を発見。抽出条件を修正し、3パターンで再確認した。"
      ]
    ]
  },
  {
    "kind": "仕事の進め方の傾向",
    "color": "purple",
    "label": "手計算を比較対象にして集計結果を確かめる",
    "reason": "初日は集計と手計算を照合し、条件修正後に3パターンで再確認した。翌日は手順をチェックリストにして別データに適用し、境界値と空欄も手計算と照合した。二つの演習に共通するのは、集計とは別の方法で結果を確かめたこと。",
    "scope": "連続する2日間の本人申告に限る。チェックリストの内容や照合結果の記録、他の業務での再現性は未確認。",
    "growth": "次の演習では境界値の直前・一致・直後と空欄について、手計算による期待値と集計結果を並べて記録する。",
    "evidence": [
      [
        "11/24 · Keep",
        "演習用の受講記録20件を集計し、手計算と照合したところ未入力1件を発見。抽出条件を修正し、3パターンで再確認した。"
      ],
      [
        "11/25 · Keep",
        "前日の集計手順をチェックリスト化し、別の演習データ10件に適用。境界値と空欄の結果を手計算と照合し、誤りがないことを確認した。"
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
function renderCandidate(c,reviewMode,i){
  const article=element("article",undefined,"card "+(c.color==="purple"?"purple-card":""));
  article.append(element("div",c.kind,"tag kind "+c.color),element("h3",c.label),element("p",c.reason),element("p","評価の範囲："+c.scope,"scope"));
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
  $("mood").textContent="未選択";$("submit").disabled=true;
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
  $("mood").textContent="充実した";filled=true;$("submit").disabled=false;$("fill").disabled=true;
});
$("submit").addEventListener("click",()=>{if(filled&&stage===0)goTo(1)});
$("analyze").addEventListener("click",()=>{
  if(stage!==1)return;
  $("analyze").disabled=true;
  $("analysis-status").textContent="解析サンプル表示完了";
  $("analysis-description").textContent="2件の原文から得た候補を再現しました。講師の確認へ進めます。";
  $("candidate-preview").hidden=false;$("review").disabled=false;
});
$("review").addEventListener("click",()=>{if(stage===1&&!$("review").disabled)review()});
$("approve").addEventListener("click",()=>{if(stage===2)approve()});
$("restart").addEventListener("click",()=>reset());
$("finish-reset").addEventListener("click",()=>reset());
reset(false);
