import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "../../lib/apiClient";
import type { ChatMessage, Department, KnowledgeItem } from "../../lib/types";

const QUICK_ASKS = ["よく聞かれる質問は？", "参考資料はどこにある？", "初日にやることは？"];
export function useOjt() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDeptId, setSelectedDeptId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [knowledge, setKnowledge] = useState<KnowledgeItem[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [escalated, setEscalated] = useState(false);
  const current = useRef(0);
  const sendingRef = useRef(false);
  useEffect(() => {
    let cancelled = false;
    apiClient.get<{ departments: Department[] }>("/api/ojt/departments").then((data) => {
      if (!cancelled) setDepartments(data.departments);
    }).catch(() => { if (!cancelled) setError("課一覧を取得できませんでした。"); });
    return () => { cancelled = true; current.current++; };
  }, []);

  const selectDept = useCallback(async (deptId: string) => {
    const version = ++current.current;
    setSelectedDeptId(deptId);
    setInput(""); setMessages([]); setKnowledge([]); setEscalated(false); setError(null);
    try {
      const [history, sources] = await Promise.all([
        apiClient.get<{ messages: ChatMessage[]; escalated: boolean }>(`/api/ojt/departments/${deptId}/messages`),
        apiClient.get<{ items: KnowledgeItem[] }>(`/api/ojt/departments/${deptId}/knowledge`),
      ]);
      if (version !== current.current) return;
      setMessages(history.messages); setKnowledge(sources.items); setEscalated(history.escalated);
    } catch {
      if (version === current.current) setError("会話を取得できませんでした。課を選び直してください。");
    }
  }, []);

  const backToDeptList = useCallback(() => {
    current.current++;
    setSelectedDeptId(null); setMessages([]); setKnowledge([]); setInput(""); setError(null);
  }, []);

  const sendMessage = async (text: string) => {
    if (!selectedDeptId || !text.trim() || sendingRef.current) return;
    const version = current.current;
    sendingRef.current = true; setSending(true); setError(null);
    try {
      const reply = await apiClient.post<ChatMessage>("/api/ojt/chat", { deptId: selectedDeptId, text });
      if (version !== current.current) return;
      setMessages((prev) => [...prev, { id: `${reply.id}-me`, role: "me", text, references: [] }, reply]);
      setInput("");
    } catch {
      if (version === current.current) setError("送信できませんでした。入力内容を確認して再送してください。");
    } finally { sendingRef.current = false; setSending(false); }
  };
  const escalate = async () => {
    if (!selectedDeptId || escalated || sendingRef.current) return;
    const version = current.current;
    sendingRef.current = true; setSending(true); setError(null);
    try {
      await apiClient.post(`/api/ojt/departments/${selectedDeptId}/escalate`, {});
      if (version === current.current) setEscalated(true);
    } catch {
      if (version === current.current) setError("相談を依頼できませんでした。先に質問を送信してください。");
    } finally { sendingRef.current = false; setSending(false); }
  };
  return { departments, selectedDept: departments.find((d) => d.id === selectedDeptId) ?? null,
    messages, knowledge, input, setInput, sending, error, escalated, escalate, selectDept,
    backToDeptList, sendMessage, quickAsks: QUICK_ASKS };
}
